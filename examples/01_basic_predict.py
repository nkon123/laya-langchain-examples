"""01. Laya 기본 사용법: 한국어/영어/일본어 문장에 대해 타입이 있는 질문에 답하기.

Laya는 텍스트를 생성하지 않는다. 입력(state)과 질문(questions)을 받아
choice / score / noul(yes-no 확률) 답을 한 번의 forward pass로 돌려준다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from laya_local import local_router  # noqa: E402

QUESTIONS = {
    "department": {
        "type": "choice",
        "instructions": "Which department should handle this?",
        "criteria": {
            "billing": "invoices, payments, refunds, duplicate charges",
            "technical": "bugs, outages, errors, login problems",
            "sales": "pricing, contracts, demos",
            "other": "everything else",
        },
    },
    "urgency": {
        "type": "score",
        "instructions": "How urgent is this?",
        "criteria": ["not urgent", "soon", "blocking"],
    },
    "churn_risk": {
        "type": "noul",
        "instructions": "Does the customer threaten to cancel or leave?",
    },
}

TEXTS = [
    "3월 요금이 두 번 결제됐어요. 중복 결제 건 환불해 주세요.",
    "로그인이 안 돼서 업무가 완전히 멈췄습니다. 오늘 안에 해결 안 되면 해지하겠습니다.",
    "Hi, could you send me pricing for the enterprise plan?",
    "請求書の金額が契約と違います。確認してください。",
]


def main():
    router = local_router()
    for text in TEXTS:
        result = router.predict(text, QUESTIONS)
        a = result["answers"]
        print(f"\n> {text}")
        print(f"  model      : {result['routing']['model']}")
        print(f"  department : {a['department']['choice']}")
        print(f"  urgency    : {a['urgency']['score']:.2f} (0=not urgent .. 2=blocking)")
        print(f"  churn_risk : {a['churn_risk']['noul']:.2f}")


if __name__ == "__main__":
    main()
