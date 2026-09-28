"""04. Laya vs 로컬 LLM: 예제 01~03과 같은 입력·같은 질문으로 비교.

Laya 쪽은 `Router.predict(text, questions)`, LLM 쪽은 같은 questions 를 프롬프트로
바꿔 OpenAI 호환 API(기본 Ollama)에 보낸다. 정답 라벨이 있는 항목만 채점한다.

    python examples/04_compare_local_llm.py                    # 전체 비교
    python examples/04_compare_local_llm.py --tasks route guard
    python examples/04_compare_local_llm.py --llm-only         # Laya 모델 없이 LLM만
    python examples/04_compare_local_llm.py --dump-prompts prompts/local_llm_prompts.md

LLM 설정: LLM_BASE_URL (기본 http://127.0.0.1:11434/v1), LLM_MODEL (기본 gemma4:latest)
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm_prompt  # noqa: E402
from samples import TASKS  # noqa: E402

NOUL_THRESHOLD = 0.5


def laya_answers(router, text, questions):
    start = time.perf_counter()
    res = router.predict(text, questions)
    seconds = time.perf_counter() - start
    out = {}
    for qid, q in questions.items():
        a = res["answers"][qid]
        if q["type"] == "choice":
            out[qid] = a["choice"]
        elif q["type"] == "score":
            out[qid] = round(a["score"])
        else:
            out[qid] = a["noul"] >= NOUL_THRESHOLD
    return out, seconds


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "Y" if v else "N"
    return str(v)


def mark(got, want):
    if want is None:
        return " "
    return "O" if got == want else "X"


def run(task_names, use_laya, use_llm):
    router = None
    if use_laya:
        from laya_local import local_router
        router = local_router()
        # Load both checkpoints up front: the english one would otherwise load on the first
        # English sample and its load time would count as inference time.
        router.preload(["english", "multilingual"])
        print(f"Laya device: {', '.join(sorted({str(a.device) for a in router._agents.values()}))}")

    summary = []
    for name in task_names:
        questions, cases = TASKS[name]
        # Warm up both sides so model load time is not counted.
        if router:
            laya_answers(router, cases[0][0], questions)
        if use_llm:
            llm_prompt.ask(cases[0][0], questions)

        print(f"\n=== {name} " + "=" * (70 - len(name)))
        stats = {"laya": [0, 0, 0.0], "llm": [0, 0, 0.0], "llm_err": 0}
        for text, expected in cases:
            print(f"\n> {text}")
            got = {}
            if router:
                got["laya"], sec = laya_answers(router, text, questions)
                stats["laya"][2] += sec
            if use_llm:
                try:
                    answers, err, sec, raw = llm_prompt.ask(text, questions)
                except Exception as e:  # network / timeout
                    answers, err, sec, raw = None, f"request failed: {e}", 0.0, ""
                got["llm"] = answers or {}
                stats["llm"][2] += sec
                if err:
                    stats["llm_err"] += 1
                    print(f"  [LLM parse] {err} :: {raw.strip()[:120]!r}")
            for qid in questions:
                want = expected.get(qid)
                cells = []
                for side in ("laya", "llm"):
                    if side not in got:
                        continue
                    v = got[side].get(qid)
                    cells.append(f"{side}={fmt(v):<16}{mark(v, want)}")
                    if want is not None:
                        stats[side][1] += 1
                        stats[side][0] += v == want
                print(f"  {qid:<17} " + "  ".join(cells) + (f"   (정답 {fmt(want)})" if want is not None else ""))
        summary.append((name, len(cases), stats))

    print("\n=== 요약 " + "=" * 64)
    print(f"{'task':<9}{'n':>3}  {'Laya 정확도':>12} {'Laya ms/건':>11}  {'LLM 정확도':>11} {'LLM ms/건':>10} {'LLM 파싱실패':>11}")
    for name, n, s in summary:
        def acc(side):
            ok, total, _ = s[side]
            return f"{ok}/{total}" if total else "-"

        def ms(side):
            return f"{s[side][2] / n * 1000:.0f}" if s[side][2] else "-"
        print(f"{name:<9}{n:>3}  {acc('laya'):>12} {ms('laya'):>11}  {acc('llm'):>11} {ms('llm'):>10} {s['llm_err'] if use_llm else '-':>11}")
    if use_llm:
        print(f"\nLLM: {os.environ.get('LLM_MODEL', 'gemma4:latest')} @ "
              f"{os.environ.get('LLM_BASE_URL', 'http://127.0.0.1:11434/v1')}")


def dump_prompts(path, task_names):
    lines = [
        "# 로컬 LLM 비교용 프롬프트",
        "",
        "Laya 예제(01~03)와 **같은 입력, 같은 질문**을 일반 LLM 프롬프트로 옮긴 것입니다.",
        "채팅 UI(Ollama, LM Studio, Open WebUI 등)에 시스템 프롬프트와 사용자 프롬프트를 그대로 붙여 넣어 보세요.",
        "`python examples/04_compare_local_llm.py --dump-prompts prompts/local_llm_prompts.md` 로 다시 생성됩니다.",
        "",
        "## 시스템 프롬프트 (모든 케이스 공통)",
        "",
        "```text",
        llm_prompt.SYSTEM_PROMPT,
        "```",
    ]
    for name in task_names:
        questions, cases = TASKS[name]
        lines += ["", f"## {name}", ""]
        for i, (text, expected) in enumerate(cases, 1):
            want = ", ".join(f"{k}={fmt(v)}" for k, v in expected.items())
            lines += [f"### {name}-{i}", "", f"정답: {want}", "", "```text",
                      llm_prompt.build_prompt(text, questions), "```", ""]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", choices=list(TASKS), default=list(TASKS))
    ap.add_argument("--llm-only", action="store_true", help="skip Laya (no model folder needed)")
    ap.add_argument("--laya-only", action="store_true", help="skip the LLM")
    ap.add_argument("--dump-prompts", metavar="PATH", help="write the LLM prompts as Markdown and exit")
    args = ap.parse_args()
    if args.dump_prompts:
        dump_prompts(args.dump_prompts, args.tasks)
    else:
        run(args.tasks, use_laya=not args.llm_only, use_llm=not args.laya_only)
