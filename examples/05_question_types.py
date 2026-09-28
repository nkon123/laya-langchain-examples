# =============================================================================
# Laya × LangChain: 질문 타입별 예제 (choice / score / noul)
# -----------------------------------------------------------------------------
# 의존성
#   - Python 3.10 이상            (테스트: Python 3.14.7, Windows 11)
#   - laya[langchain]==0.3.21     (langchain-core, torch, transformers 함께 설치됨)
#       테스트 버전: langchain-core 1.6.5, torch 2.14.0(CPU), transformers 5.17.0
#
# 설치
#   pip install "laya[langchain]==0.3.21"
#
# 모델
#   - 첫 실행 시 Hugging Face(convaiinnovations/laya)에서 자동 다운로드
#     (한국어 입력은 multilingual 체크포인트 약 0.7GB 사용)
#   - 미리 받아 둔 폴더를 쓰려면 환경변수로 지정:
#       PowerShell : $env:LAYA_MODEL_DIR = "C:\models\laya"
#       bash       : export LAYA_MODEL_DIR=/models/laya
#
# 실행
#   python 05_question_types.py
# =============================================================================
"""Laya의 세 가지 질문 타입을 LangChain Runnable로 쓰는 예제.

    choice : 보기 중 하나 고르기       -> LayaRouter    -> RunnableBranch 로 분기
    score  : 순서가 있는 등급 매기기   -> LayaEvaluator -> 우선순위(P1~P3)로 변환
    noul   : 예/아니오 확률            -> LayaEvaluator -> 임계값으로 True/False 판정

마지막에 RunnableParallel 로 세 판단을 한 번에 실행한다.
"""
import os

from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnableParallel
from laya import Router
from laya.integrations.langchain import LayaEvaluator, LayaRouter


# -----------------------------------------------------------------------------
# 1. 모델 준비
# -----------------------------------------------------------------------------
def build_router() -> Router:
    """LAYA_MODEL_DIR 이 있으면 로컬 폴더에서, 없으면 Hugging Face 에서 모델을 읽는다."""
    model_dir = os.environ.get("LAYA_MODEL_DIR")
    if not model_dir:
        return Router()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # 로컬 폴더만 사용, 외부 접속 안 함
    return Router(models={
        "english": (model_dir, None),                # <폴더>/model.safetensors
        "multilingual": (model_dir, "multilingual"),  # <폴더>/multilingual/model.safetensors
    })


# 입력 언어를 감지해 영어/다국어 체크포인트로 자동 분기한다. 아래 세 체인이 함께 쓴다.
router = build_router()


# -----------------------------------------------------------------------------
# 2. choice: 담당 팀 고르기
#    Laya 답 예) {"choice": "billing", "answer_confidence": 0.83, "probabilities": {...}}
#    LayaRouter 는 라벨 문자열만 돌려주고, 확신도가 임계값보다 낮으면 fallback 을 돌려준다.
# -----------------------------------------------------------------------------
choose_team = LayaRouter(
    instructions="이 고객 문의는 어느 팀이 처리해야 하나요?",
    criteria={
        "billing": "결제, 청구서, 중복 결제, 환불",
        "tech": "오류, 버그, 장애, 로그인 실패",
        "sales": "가격 견적, 요금제, 계약, 데모",
    },
    confidence_threshold=0.7,  # 확신도 0.7 미만이면
    fallback="human",          # 상담원에게 넘긴다
    agent=router,
)

choice_chain = choose_team | RunnableBranch(
    (lambda team: team == "billing", RunnableLambda(lambda _: "결제팀으로 전달")),
    (lambda team: team == "tech", RunnableLambda(lambda _: "기술지원팀으로 전달")),
    (lambda team: team == "sales", RunnableLambda(lambda _: "영업팀으로 전달")),
    RunnableLambda(lambda _: "상담원 확인 필요"),  # 기본 분기 (human)
)


# -----------------------------------------------------------------------------
# 3. score: 긴급도 등급 매기기
#    Laya 답 예) {"score": 1.74, "probabilities": {"0": 0.03, "1": 0.19, "2": 0.77}}
#               ("로그인이 안 돼서 업무가 완전히 멈췄습니다." 입력 시)
#    score 는 등급의 기댓값(0 ~ 등급 수-1)이다. 반올림하면 가장 가까운 등급이 된다.
#    실측: 한국어 입력에는 한국어 문구가 등급을 더 잘 구분했다.
#          (영어 문구는 견적 문의까지 1.7 이상으로 몰림)
# -----------------------------------------------------------------------------
URGENCY_LEVELS = ["급하지 않음", "빠른 처리 필요", "업무가 멈춤"]
PRIORITIES = ["P3", "P2", "P1"]

rate_urgency = LayaEvaluator(
    questions={
        "urgency": {
            "type": "score",
            "instructions": "이 문의는 얼마나 급한가요?",
            "criteria": URGENCY_LEVELS,  # 순서대로 0, 1, 2 등급
        },
    },
    agent=router,
)


def to_priority(answers: dict) -> dict:
    score = answers["urgency"]["score"]
    level = round(score)
    return {"score": round(score, 2), "level": URGENCY_LEVELS[level], "priority": PRIORITIES[level]}


score_chain = rate_urgency | RunnableLambda(to_priority)


# -----------------------------------------------------------------------------
# 4. noul: 환불 요청 여부 판단
#    Laya 답 예) {"noul": 0.93}   <- "예"일 확률 (0 ~ 1)
#    임계값은 업무에 맞게 정한다. 놓치면 안 되는 항목이면 낮게, 오탐이 비싸면 높게.
#    실측: noul 은 문구에 민감했다. 이 영어 문구는 5건 중 4건을 맞혔고,
#          "환불 가능한가요?" 같은 완곡한 요청은 놓쳤다.
# -----------------------------------------------------------------------------
REFUND_THRESHOLD = 0.5

detect_refund = LayaEvaluator(
    questions={
        "refund": {
            "type": "noul",
            "instructions": "Does the customer ask for money back?",
        },
    },
    agent=router,
)

noul_chain = detect_refund | RunnableLambda(lambda answers: {
    "probability": round(answers["refund"]["noul"], 2),
    "refund": answers["refund"]["noul"] >= REFUND_THRESHOLD,
})


# -----------------------------------------------------------------------------
# 5. 세 판단을 한 번에 실행
# -----------------------------------------------------------------------------
all_in_one = RunnableParallel(team=choice_chain, urgency=score_chain, refund=noul_chain)


if __name__ == "__main__":
    # 체인을 하나씩 실행
    text = "지난달 청구서에 중복 결제가 있습니다. 돈 돌려주세요."
    print(f"> {text}")
    print("  [choice]", choice_chain.invoke(text))  # 결제팀으로 전달
    print("  [score] ", score_chain.invoke(text))   # {'score': 1.41, 'level': '빠른 처리 필요', 'priority': 'P2'}
    print("  [noul]  ", noul_chain.invoke(text))    # {'probability': 0.93, 'refund': True}

    # 세 체인을 한 번에 실행
    for text in [
        "카드가 두 번 결제됐는데 환불 가능한가요?",  # refund 를 놓치는 사례
        "API가 500 에러를 계속 반환합니다.",
        "엔터프라이즈 요금제 견적 부탁드립니다.",
        "로그인이 안 돼서 업무가 완전히 멈췄습니다.",
    ]:
        print(f"\n> {text}")
        for key, value in all_in_one.invoke(text).items():
            print(f"  {key:<8}: {value}")
