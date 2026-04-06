# OndeviceLLLM

간단한 로컬 Qwen 모델 실행 예제입니다. 이 프로젝트는 Hugging Face `transformers`를 사용해 로컬에 저장된 `Qwen/Qwen3-0.6B` 모델을 불러와서 간단한 채팅입력을 처리합니다.

## 구성

- `qwen.py`: 모델 로딩 및 텍스트 생성용 스크립트
- `file_path.data`: 모델 스냅샷 폴더 이름을 저장하는 파일
- `../models/models--Qwen--Qwen3-0.6B/`: 모델 체크포인트가 위치하는 상위 폴더
- `../models/models--Qwen--Qwen3-0.6B/snapshots/`: 실제 스냅샷 폴더

## 필요 조건

- Python 3.11 이상 권장
- `transformers` 라이브러리

```powershell
pip install transformers
```

## 사용 방법

1. 모델 데이터를 준비합니다.
   - `Qwen/Qwen3-0.6B` 모델을 로컬에 다운로드하거나 `../models/models--Qwen--Qwen3-0.6B/snapshots/` 폴더 안에 한 개 이상의 모델 스냅샷 폴더를 둡니다.

2. 현재 작업 디렉터리는 `qwen.py`가 있는 폴더여야 합니다.

3. 스크립트를 실행합니다.

```powershell
python qwen.py
```

## 동작 방식

`qwen.py`는 다음과 같은 로직을 따릅니다:

- `../models/models--Qwen--Qwen3-0.6B` 폴더가 존재하면 내부 `snapshots` 폴더에서 첫 번째 서브폴더 이름을 `file_path.data`에 기록하고 해당 경로에서 로컬 모델과 토크나이저를 불러옵니다.
- 존재하지 않으면 Hugging Face 허브에서 `Qwen/Qwen3-0.6B` 모델을 다운로드해서 `../models` 캐시 디렉터리에 저장합니다.
- 기본 메시지 `불을 끄기 위한 거를 json으로 대답해`를 `tool` 역할로 전달하고 `apply_chat_template`를 사용해 입력을 준비합니다.

## 오류 및 주의 사항

`ValueError: Cannot use chat template functions because tokenizer.chat_template is not set and no template argument was passed!` 오류가 발생하면 다음을 확인하세요:

- 모델 토크나이저가 `chat_template`를 지원하는지 확인해야 합니다.
- `AutoTokenizer`로 불러온 토크나이저가 직접 대화 템플릿을 제공하지 않는 경우, `tokenizer.apply_chat_template(...)` 대신 일반 `tokenizer(...)`를 사용하거나 채팅 템플릿을 직접 설정해야 합니다.

### 예시 해결 방법

토크나이저가 `chat_template`를 제공하지 않으면, `qwen.py`에서 `apply_chat_template` 호출을 다음과 같이 변경할 수 있습니다:

```python
inputs = self.tokenizer(
    self._message,
    return_tensors="pt",
    truncation=True,
)
```

그리고 모델 출력 디코딩 시 `input_ids` 길이를 기준으로 출력 슬라이싱을 조정합니다.

## 참고

- Hugging Face Transformers 문서: https://huggingface.co/docs/transformers/main/en/chat_templating
- 모델 경로가 상대 경로이므로, `qwen.py`를 실행할 때 현재 디렉터리를 반드시 확인하세요.

## 개선 아이디어

- `file_path.data`가 없을 때 안전하게 처리하는 로직 추가
- 모델 로딩 경로를 환경 변수나 CLI 인자로 변경
- 채팅 템플릿 지원 여부를 자동 검사하는 코드 추가
