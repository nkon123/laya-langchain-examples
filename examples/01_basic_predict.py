"""01. Laya 기본 사용법: 한국어/영어/일본어 문장에 대해 타입이 있는 질문에 답하기.

Laya는 텍스트를 생성하지 않는다. 입력(state)과 질문(questions)을 받아
choice / score / noul(yes-no 확률) 답을 한 번의 forward pass로 돌려준다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from laya_local import local_router  # noqa: E402
from samples import CLASSIFY_CASES, CLASSIFY_QUESTIONS  # noqa: E402

QUESTIONS = CLASSIFY_QUESTIONS
TEXTS = [text for text, _ in CLASSIFY_CASES]


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
