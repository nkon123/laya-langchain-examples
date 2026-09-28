# laya-langchain-examples

[Laya](https://github.com/NandhaKishorM/laya)를 **LangChain / LangGraph**에서 쓰는 예제 모음입니다.
모델은 로컬 폴더에서 읽고, Hugging Face Hub에 접속하지 않도록 구성했습니다.

Laya는 텍스트를 생성하는 LLM이 아닙니다. 입력 텍스트와 "타입이 있는 질문"을 받아
`choice`(분류), `score`(등급), `noul`(예/아니오 확률)을 한 번의 forward pass로 돌려주는
결정 모델이라서 라우팅, 가드레일, 티켓 분류 같은 역할에 적합합니다. 100개 이상의 언어를 지원합니다.

| 예제 | 내용 |
|---|---|
| `examples/01_basic_predict.py` | `Router.predict` 기본 사용. 한/영/일 문장 → 부서·긴급도·이탈위험 |
| `examples/02_langchain_lcel.py` | LCEL: `LayaGuardrail` → `LayaRouter` → `RunnableBranch` |
| `examples/03_langgraph_support.py` | LangGraph: guard → triage → 조건부 엣지(`LayaRouter`) → 팀별 노드 |
| `examples/04_compare_local_llm.py` | 같은 입력·같은 질문으로 Laya와 로컬 LLM(Ollama 등) 비교 |
| `examples/05_question_types.py` | 질문 타입별 LCEL: choice(`LayaRouter`) / score·noul(`LayaEvaluator`) / `RunnableParallel` |

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

## 설치 (Windows, Python 3.14)

### 준비물
- Windows 10/11 x64
- **Python 3.14** (python.org 설치본 권장)
- 모델 폴더 `laya/` (`model.safetensors`, `multilingual/`, `typed-decisions/`)

### 1. 설치

```powershell
git clone https://github.com/nkon123/laya-langchain-examples
cd laya-langchain-examples
.\scripts\install.ps1 -ModelDir C:\laya\laya
```

`install.ps1`은 `nvidia-smi`로 CUDA 버전을 확인해 맞는 PyTorch(cu130 / cu126 / cpu)를 먼저 설치하고,
`requirements.txt`를 설치한 뒤 예제 01을 실행합니다. 빌드를 직접 고르려면 `-Cuda cu126` 처럼 지정합니다.
CPU만 쓸 때 직접 하려면:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> 애플리케이션 제어 정책이 있는 PC에서는 `pip.exe` 등 venv 안의 실행 파일이 차단될 수 있습니다.
> 항상 `python.exe -m pip` 형태로 실행하세요.

### 2. 실행

```powershell
$env:LAYA_MODEL_DIR = "C:\laya\laya"     # 영구 등록: setx LAYA_MODEL_DIR "C:\laya\laya"
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe examples\01_basic_predict.py
.\.venv\Scripts\python.exe examples\02_langchain_lcel.py
.\.venv\Scripts\python.exe examples\03_langgraph_support.py
```

`laya_local.py`가 `HF_HUB_OFFLINE=1`을 설정하므로 모델은 로컬 폴더에서만 읽습니다.
CPU에서 한 건당 수백 ms 정도 걸립니다.

## 로컬 LLM과 비교 (04)

`samples.py`에 예제 01~03의 입력, 질문, 정답 라벨이 모여 있습니다. `04_compare_local_llm.py`는
Laya의 질문 정의를 그대로 프롬프트로 바꿔 OpenAI 호환 API(Ollama, LM Studio, vLLM 등)에 보내고,
정확도, 건당 응답 시간, JSON 파싱 실패를 비교합니다.

```powershell
$env:LLM_BASE_URL = "http://127.0.0.1:11434/v1"   # Ollama 기본값
$env:LLM_MODEL = "gemma4:latest"
.\.venv\Scripts\python.exe examples\04_compare_local_llm.py                # 전체
.\.venv\Scripts\python.exe examples\04_compare_local_llm.py --tasks route  # 일부만
```

채팅 UI에 직접 붙여 넣어 볼 프롬프트는 [`prompts/local_llm_prompts.md`](prompts/local_llm_prompts.md)에 있습니다.

측정 예 (Laya: Ryzen 7 9800X3D CPU / RTX 5080 GPU fp16, gemma4 8B Q4: Ollama, RTX 5080 GPU):

| task | n | Laya 정확도 | Laya CPU ms/건 | Laya GPU ms/건 | LLM 정확도 | LLM ms/건 |
|---|---|---|---|---|---|---|
| classify | 4 | 7/8 | 171 | 36 | 8/8 | 2,063 |
| route | 6 | 4/6 | 74 | 28 | 6/6 | 2,679 |
| guard | 8 | 14/16 | 91 | 30 | 16/16 | 1,024 |
| triage | 3 | 8/11 | 255 | 31 | 11/11 | 4,005 |

- 이 샘플에서는 8B LLM이 모두 맞혔고, Laya는 한국어 문의에서 이탈 위험·긴급도·영업 문의를 놓쳤습니다.
- Laya는 CPU에서도 LLM(GPU)보다 11~36배, 같은 GPU에서는 34~130배 빨랐습니다. GPU 없는 PC라면 LLM은 훨씬 더 느려집니다.
- Laya는 답이 항상 정해진 형식(선택지/확률)으로 나와 파싱 실패가 없고, 확률을 임계값으로 조정할 수 있습니다.
- 21건, 정답 라벨은 작성자 판단이라 벤치마크가 아닙니다. 실제 판단은 자체 데이터로 하세요.

## GPU로 실행 (NVIDIA)

laya는 PyTorch가 CUDA를 인식하면 자동으로 GPU를 씁니다. `scripts\install.ps1`이 아래를 자동으로 처리합니다.

| `nvidia-smi`의 CUDA 버전 | 설치할 PyTorch | 예 |
|---|---|---|
| 13.x | `cu130` | RTX 50 시리즈 (sm_120은 cu130 필요) |
| 12.x | `cu126` | RTX 20/30/40 시리즈 + CUDA 12 드라이버 |
| 없음 / 11 이하 | `cpu` | GPU 없음, 드라이버 업데이트 필요 |

직접 설치할 때는 **CUDA 빌드 torch를 먼저** 설치합니다.

```powershell
.\.venv\Scripts\python.exe -m pip uninstall -y torch     # 이미 CPU torch가 있으면
.\.venv\Scripts\python.exe -m pip install torch --no-cache-dir --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

- `Torch not compiled with CUDA enabled` 는 CPU 빌드(`2.14.0+cpu`)가 깔린 상태입니다. pip는 버전이 같으면
  `Requirement already satisfied`로 넘어가므로 위처럼 먼저 지우고 설치하세요.
- 빌드가 `+cu126`인데 `False`면 드라이버 문제입니다. `nvidia-smi`로 확인하세요.
- GPU에서는 기본으로 bf16 autocast를 씁니다. 이 샘플에서는 bf16일 때 라우팅 1건이 CPU와 달라졌고,
  **`$env:LAYA_CUDA_AMP = "fp16"`** 으로 두면 CPU와 같은 결과가 나왔습니다. `install.ps1`은 fp16으로 실행합니다.
- 장치를 직접 고르려면 `local_router(device="cuda")` 또는 `local_router(device="cpu")`.
  `laya-serve`는 `LAYA_DEVICE`, CLI는 `--device`.
- VRAM 6GB급 GPU에서 로컬 LLM과 같이 올리면 메모리가 빠듯합니다. 04 예제는 `--laya-only` / `--llm-only`로 나눠 돌리세요.
- `04_compare_local_llm.py`는 첫 줄에 사용 장치를 출력합니다.

## 외부 통신 검토 (laya 0.3.21)

- 패키지 소스에 텔레메트리, 외부 프로세스 실행, `eval`/`exec`, pickle 로딩이 없습니다.
  모델은 safetensors라 로드 시 코드가 실행되지 않습니다.
- Python audit hook으로 예제 3개 실행 중 소켓 연결·DNS 조회·프로세스 실행을 기록한 결과 0건이었습니다.
- 아래 설정을 쓰면 외부 통신이 생깁니다. 예제는 모두 사용하지 않습니다.

| 조건 | 동작 |
|---|---|
| `LayaRouter` 등에 `base_url` 지정 | 입력 텍스트를 그 서버로 전송 |
| 로컬 경로 없이 `Router()` 사용 | Hugging Face에서 모델 다운로드 |
| `LANGSMITH_TRACING=true` + API 키 | LangChain이 입출력을 LangSmith로 전송 |
| `laya-serve` 실행 | 기본 `0.0.0.0`, 인증 없음 → `LAYA_HOST=127.0.0.1`, `LAYA_API_KEY` 설정 권장 |

검토한 버전으로 고정하기 위해 `requirements.txt`는 `laya[langchain]==0.3.21`입니다.
올릴 때는 변경 내용을 다시 확인하세요.

## 실측 결과와 한계 (CPU, Python 3.14, laya 0.3.21)

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
