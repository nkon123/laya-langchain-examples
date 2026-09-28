"""Ask a local LLM the same typed questions Laya answers, through a plain prompt.

The prompt is built from the Laya `questions` dict, so both sides get the same
instructions and criteria. The LLM is reached through an OpenAI-compatible
`/chat/completions` endpoint (Ollama, LM Studio, vLLM, llama.cpp server):

    LLM_BASE_URL  default http://127.0.0.1:11434/v1   (Ollama)
    LLM_MODEL     default gemma4:latest
    LLM_API_KEY   optional bearer token
"""
import json
import os
import re
import time
import urllib.request

SYSTEM_PROMPT = (
    "You are a classifier. Read the text and answer every question. "
    "Reply with a single JSON object only, no explanation."
)


def _question_lines(questions):
    lines, keys = [], []
    for qid, q in questions.items():
        t = q["type"]
        if t == "choice":
            opts = "\n".join(f'    - "{k}": {v}' if v else f'    - "{k}"'
                             for k, v in q["criteria"].items())
            lines.append(f'- "{qid}": {q["instructions"]}\n  Answer with exactly one of:\n{opts}')
            keys.append(f'"{qid}": "<option>"')
        elif t == "score":
            levels = "\n".join(f"    {i} = {c}" for i, c in enumerate(q["criteria"]))
            lines.append(f'- "{qid}": {q["instructions"]}\n  Answer with an integer level:\n{levels}')
            keys.append(f'"{qid}": <integer>')
        elif t == "noul":
            lines.append(f'- "{qid}": {q["instructions"]}\n  Answer true or false.')
            keys.append(f'"{qid}": true|false')
        else:
            raise ValueError(f"unsupported question type {t!r}")
    return "\n".join(lines), "{" + ", ".join(keys) + "}"


def build_prompt(text, questions):
    """User prompt for one text. `prompt`/`message` in the Laya instructions refer to the text."""
    body, shape = _question_lines(questions)
    return (
        f"Text:\n\"\"\"\n{text}\n\"\"\"\n\n"
        f"Questions (`prompt` and `message` below mean the text above):\n{body}\n\n"
        f"Reply in this JSON shape:\n{shape}"
    )


def parse_answer(content, questions):
    """Pull the first JSON object out of the reply and normalise it. Returns (answers, error)."""
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None, "no JSON in reply"
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return None, f"invalid JSON: {e.msg}"
    answers = {}
    for qid, q in questions.items():
        v = raw.get(qid)
        if q["type"] == "choice":
            answers[qid] = v if v in q["criteria"] else None
        elif q["type"] == "score":
            answers[qid] = int(v) if isinstance(v, (int, float)) else None
        else:
            answers[qid] = v if isinstance(v, bool) else (
                str(v).lower() in ("true", "yes") if v is not None else None)
    missing = [k for k, v in answers.items() if v is None]
    return answers, (f"missing/invalid: {', '.join(missing)}" if missing else None)


def ask(text, questions, timeout=120):
    """Returns (answers, error, seconds, raw_reply)."""
    base = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
    payload = {
        "model": os.environ.get("LLM_MODEL", "gemma4:latest"),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(text, questions)},
        ],
    }
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LLM_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['LLM_API_KEY']}"
    req = urllib.request.Request(f"{base}/chat/completions", json.dumps(payload).encode(), headers)
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = json.load(resp)["choices"][0]["message"]["content"] or ""
    seconds = time.perf_counter() - start
    answers, error = parse_answer(content, questions)
    return answers, error, seconds, content
