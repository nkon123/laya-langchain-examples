# laya-langchain-examples

[Laya](https://github.com/NandhaKishorM/laya)를 **LangChain / LangGraph**에서 쓰는 예제 모음입니다.
**인터넷이 막힌 사내 PC**에서 로컬 모델 폴더만으로 돌아가도록 구성했습니다.

Laya는 텍스트를 생성하는 LLM이 아닙니다. 입력 텍스트와 "타입이 있는 질문"을 받아
`choice`(분류), `score`(등급), `noul`(예/아니오 확률)을 한 번의 forward pass로 돌려주는
결정 모델이라서 라우팅, 가드레일, 티켓 분류 같은 역할에 적합합니다. 100개 이상의 언어를 지원합니다.

| 예제 | 내용 |
|---|---|
| `examples/01_basic_predict.py` | `Router.predict` 기본 사용. 한/영/일 문장 → 부서·긴급도·이탈위험 |
| `examples/02_langchain_lcel.py` | LCEL: `LayaGuardrail` → `LayaRouter` → `RunnableBranch` |
| `examples/03_langgraph_support.py` | LangGraph: guard → triage → 조건부 엣지(`LayaRouter`) → 팀별 노드 |

외부 LLM은 호출하지 않습니다. 팀별 노드는 자리표시자이므로, 사내 LLM(Ollama, vLLM 등)이 있으면 그 자리에 연결하면 됩니다.

## 모델 체크포인트

HF 저장소 `convaiinnovations/laya`에 세 체크포인트가 함께 들어 있습니다 (Apache-2.0).

| 이름 | 폴더 | 크기 | 용도 |
|---|---|---|---|
| english | `laya/` (루트) | 843 MB | 영어 |
| multilingual | `laya/multilingual/` | 678 MB | 100+ 언어 (한국어 포함). `convaiinnovations/laya-multilingual`과 동일 파일 |
| typed-decisions | `laya/typed-decisions/` | 846 MB | 고객상담·인보이스·보안사고 등 정형 워크플로 |

`Router`는 입력 언어를 감지해서 영어는 english, 그 외는 multilingual로 자동 분기합니다.
english 폴더가 없으면 영어 입력도 multilingual이 처리합니다 (`laya_local.py` 참고).

## 사내 PC 설치 (오프라인)

### 준비물
- Windows 10/11 x64
- **Python 3.11** (python.org 설치본 권장). 휠 번들이 3.11용으로 받아져 있습니다.
- 모델 폴더 `laya/`와 휠 번들 `wheels-py311/`

### 1. 폴더 배치

```
C:\laya\
├─ laya\                     ← 모델 (model.safetensors, multilingual\, typed-decisions\)
├─ wheels-py311\             ← 오프라인 설치용 휠
└─ laya-langchain-examples\  ← 이 저장소
```

### 2. 가상환경 만들고 오프라인 설치 (PowerShell)

```powershell
cd C:\laya\laya-langchain-examples
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links ..\wheels-py311 "laya[langchain]" langgraph
.\.venv\Scripts\python.exe -c "import laya, torch; print(laya.__version__, torch.__version__)"
```

`scripts\install_offline.ps1`이 위 과정을 한 번에 수행합니다.

> 사내 PC에 애플리케이션 제어 정책이 있으면 `pip.exe` 등 venv 안의 실행 파일이 차단될 수 있습니다.
> 항상 `python.exe -m pip` 형태로 실행하고, 그래도 막히면 보안팀에 Python 실행 허용을 요청하세요.

### 3. 실행

```powershell
$env:LAYA_MODEL_DIR = "C:\laya\laya"
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe examples\01_basic_predict.py
.\.venv\Scripts\python.exe examples\02_langchain_lcel.py
.\.venv\Scripts\python.exe examples\03_langgraph_support.py
```

`laya_local.py`가 `HF_HUB_OFFLINE=1`을 설정하므로 외부 네트워크에 접속하지 않습니다.
CPU에서 한 건당 수백 ms 정도 걸립니다.

### 인터넷이 되는 PC라면

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# 모델은 첫 실행 때 자동 다운로드되며, 로컬 폴더를 쓰려면 LAYA_MODEL_DIR을 지정합니다.
```

### 휠 번들을 다시 만들려면 (인터넷 되는 PC)

```powershell
python -m pip download "laya[langchain]" langgraph -d wheels-py311 `
  --platform win_amd64 --python-version 3.11 --only-binary=:all: `
  --extra-index-url https://download.pytorch.org/whl/cpu
```

## 실측 결과와 한계 (CPU, laya 0.3.21)

- **01 기본 분류**: 한국어·일본어 결제/장애 문의의 부서 분류와 긴급도는 기대대로 나왔습니다.
- **라우팅**: 한국어 입력은 criteria를 한국어로 쓸 때 더 안정적입니다. 6개 샘플 중 4개가 정답이었고,
  오답은 확신도가 낮게(0.4–0.6) 나와서 `confidence_threshold=0.7`로 상담원(fallback)에게 넘깁니다.
  실제 적용 전에 자체 데이터로 criteria 문구와 임계값을 조정하세요.
- **가드레일**: 기본 preset의 `harm_severity`는 평범한 한국어 문의도 높게 채점해서 오탐이 많습니다.
  예제에서는 `jailbreak`·`prompt_injection` 두 항목만 씁니다(`support_config.py`).
  그래도 "오늘 해결 안 되면 계약 해지합니다!"처럼 강한 명령·위협 어조의 정상 문의를
  인젝션으로 판단하는 사례가 있습니다.

## 라이선스

예제 코드: MIT. Laya 모델과 패키지: Apache-2.0 (Convai Innovations).
