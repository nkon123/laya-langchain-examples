"""05. 질문 타입별 LangChain 예제: choice / score / noul.

    choice : 보기 중 하나 고르기      -> LayaRouter 로 라벨을 받고 RunnableBranch 로 분기
    score  : 순서가 있는 등급 매기기  -> LayaEvaluator 로 기댓값·등급별 확률을 받아 우선순위로 변환
    noul   : 예/아니오 확률           -> LayaEvaluator 로 확률을 받아 임계값으로 판정

마지막에 RunnableParallel 로 세 가지를 한 번에 돌린다.

한국어 입력에서 측정한 것 (laya 0.3.21, multilingual):
- score: 영어 문구("not urgent/soon/blocking")는 견적 문의까지 1.7 이상으로 몰렸고,
  한국어 문구는 견적 1.0, 업무 중단 1.7 로 구분됐다. 그래서 한국어 문구를 쓴다.
- noul: 문구에 민감하다. "해지/이탈" 질문은 영어·한국어 모두 무관한 문장에 높은 확률이 나와
  쓸 만한 임계값이 없었다. 여기서는 5건 중 4건을 맞힌 영어 "환불 요청" 질문을 쓴다
  ("환불 가능한가요?"는 여전히 놓친다). 실제로 쓰기 전에 자체 데이터로 문구와 임계값을 확인할 것.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from laya_local import local_router  # noqa: E402

from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnableParallel  # noqa: E402
from laya.integrations.langchain import LayaEvaluator, LayaRouter  # noqa: E402

agent = local_router()

# --- choice ---------------------------------------------------------------
# 답: {"choice": "billing", "probabilities": {...}, "answer_confidence": 0.83}
# LayaRouter 는 choice 라벨만 돌려주고, 확신도가 임계값보다 낮으면 fallback 을 돌려준다.
choose_team = LayaRouter(
    criteria={
        "billing": "결제, 청구서, 중복 결제, 환불",
        "tech": "오류, 버그, 장애, 로그인 실패",
        "sales": "가격 견적, 요금제, 계약, 데모",
    },
    instructions="이 고객 문의는 어느 팀이 처리해야 하나요?",
    confidence_threshold=0.7,
    fallback="human",
    agent=agent,
)

choice_chain = choose_team | RunnableBranch(
    (lambda team: team == "billing", RunnableLambda(lambda _: "결제팀으로 전달")),
    (lambda team: team == "tech", RunnableLambda(lambda _: "기술지원팀으로 전달")),
    (lambda team: team == "sales", RunnableLambda(lambda _: "영업팀으로 전달")),
    RunnableLambda(lambda _: "상담원 확인 필요"),
)

# --- score ----------------------------------------------------------------
# 답: {"score": 1.74, "probabilities": {"0": ..., "1": ..., "2": ...}, "legend": {...}}
# score 는 등급의 기댓값(0 ~ k-1)이다. 반올림하면 가장 가까운 등급이 된다.
URGENCY = ["급하지 않음", "빠른 처리 필요", "업무가 멈춤"]
rate_urgency = LayaEvaluator(
    questions={"urgency": {"type": "score", "instructions": "이 문의는 얼마나 급한가요?",
                           "criteria": URGENCY}},
    agent=agent,
)


def to_priority(answers):
    a = answers["urgency"]
    level = round(a["score"])
    return {"score": round(a["score"], 2), "level": URGENCY[level], "priority": ["P3", "P2", "P1"][level]}


score_chain = rate_urgency | RunnableLambda(to_priority)

# --- noul -----------------------------------------------------------------
# 답: {"noul": 0.93}  (예일 확률 0~1)
# 임계값은 업무에 맞게 정한다. 놓치면 안 되는 항목이면 낮게, 오탐이 비싸면 높게.
detect_refund = LayaEvaluator(
    questions={"refund": {"type": "noul", "instructions": "Does the customer ask for money back?"}},
    agent=agent,
)
REFUND_THRESHOLD = 0.5
noul_chain = detect_refund | RunnableLambda(
    lambda a: {"probability": round(a["refund"]["noul"], 2), "refund": a["refund"]["noul"] >= REFUND_THRESHOLD}
)

# --- 세 가지를 한 번에 ------------------------------------------------------
all_in_one = RunnableParallel(team=choice_chain, urgency=score_chain, refund=noul_chain)

if __name__ == "__main__":
    text = "지난달 청구서에 중복 결제가 있습니다. 돈 돌려주세요."
    print("[choice]", choice_chain.invoke(text))
    print("[score] ", score_chain.invoke(text))
    print("[noul]  ", noul_chain.invoke(text))

    for text in [
        "카드가 두 번 결제됐는데 환불 가능한가요?",  # refund 를 놓치는 사례 (docstring 참고)
        "API가 500 에러를 계속 반환합니다.",
        "엔터프라이즈 요금제 견적 부탁드립니다.",
        "로그인이 안 돼서 업무가 완전히 멈췄습니다.",
    ]:
        print(f"\n> {text}")
        for key, value in all_in_one.invoke(text).items():
            print(f"  {key:<8}: {value}")
