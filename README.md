# SLM Control

Raspberry Pi에서 음성 명령을 받아 로컬 Qwen 분류 모델로 명령을 해석하고, 서보 모터를 제어하는 멀티프로세스 제어 시스템입니다.

현재 구성은 다음 흐름으로 동작합니다.

```text
ReSpeaker 2-Mics Pi HAT v2
  -> arecord
  -> Google Cloud Speech-to-Text
  -> parsing.py
  -> Qwen3-0.6B command classifier
  -> servo_control.py
  -> pigpio / servo
```

## 주요 파일

- `main.py`: 전체 프로세스 실행/종료 관리자
- `stt.py`: ReSpeaker 오디오 캡처 및 Google Cloud Speech-to-Text
- `parsing.py`: STT 텍스트 수신, Qwen 명령 분류, 서보 노드로 JSON 전송
- `qwen.py`: 로컬 Qwen3-0.6B 기반 명령 분류
- `servo_control.py`: pigpio를 통한 서보 모터 제어
- `requirements.txt`: Python 의존성 목록

## 하드웨어

- Raspberry Pi
- ReSpeaker 2-Mics Pi HAT v2
- Servo motor on GPIO 12
- `pigpio` daemon

ReSpeaker v2는 `TLV320AIC3104/tlv320aic3x` codec을 사용합니다. 기존 ReSpeaker v1용 `seeed-voicecard`/`wm8960` 설정과 섞이면 녹음이 깨질 수 있습니다.

## 부팅 설정

`/boot/firmware/config.txt`에는 ReSpeaker v2 overlay만 활성화합니다.

```text
#dtparam=i2s=on
#dtparam=audio=on
dtoverlay=respeaker-2mic-v2_0
```

중요:

- `dtparam=audio=on`을 켜면 온보드 오디오가 올라오면서 ReSpeaker I2S와 충돌할 수 있습니다.
- `dtparam=i2s=on`은 v2 overlay와 함께 수동으로 켜지 않아도 됩니다.
- overlay 파일은 `/boot/firmware/overlays/respeaker-2mic-v2_0.dtbo`에 있어야 합니다.

## pigpiod 주의

절대 아래처럼 실행하지 마세요.

```bash
sudo pigpiod
```

`pigpiod` 기본값은 PCM clock을 사용합니다.

```text
-t value, clock peripheral, 0=PWM 1=PCM, default PCM
```

ReSpeaker도 I2S/PCM을 사용하므로 `sudo pigpiod`를 실행하면 `arecord`가 `overrun`을 내거나 5초 녹음이 0.1초 만에 끝나는 문제가 생깁니다.

반드시 이렇게 실행합니다.

```bash
sudo pigpiod -t 0
```

이미 `sudo pigpiod`로 I2S가 깨졌다면 `sudo pigpiod -t 0`으로 다시 켜도 바로 복구되지 않을 수 있습니다. 그때는 재부팅하세요.

```bash
sudo reboot
```

## 설치

가상환경이 이미 있다면:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Google Cloud STT 클라이언트와 Qwen/서보 관련 의존성이 필요합니다.

```bash
python3 -c "from google.cloud import speech; print('google speech ok')"
```

## Google Cloud 인증

`stt.py`는 Google Cloud Speech-to-Text API를 사용합니다. 실행 전에 서비스 계정 JSON 키 경로를 `GOOGLE_APPLICATION_CREDENTIALS`에 지정해야 합니다.

예:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/home/pi/Documents/SLM_Control/google-stt-key.json
```

주의:

- 이 `export`는 현재 터미널 세션에만 적용됩니다.
- 재부팅하거나 새 터미널을 열면 다시 설정해야 합니다.
- JSON 키 파일은 비밀번호처럼 취급하고 GitHub 등에 올리지 마세요.

매번 입력하기 싫으면 `~/.bashrc`에 추가합니다.

```bash
echo 'export GOOGLE_APPLICATION_CREDENTIALS=/home/pi/Documents/SLM_Control/google-stt-key.json' >> ~/.bashrc
source ~/.bashrc
```

현재 설정 확인:

```bash
echo $GOOGLE_APPLICATION_CREDENTIALS
```

아무것도 출력되지 않으면 인증 경로가 설정되지 않은 상태입니다.

## 실행 전 점검

1. `pigpiod`가 `-t 0`으로 떠 있는지 확인합니다.

```bash
pgrep -af pigpiod
```

정상 예:

```text
5891 pigpiod -t 0
```

2. ReSpeaker 캡처 카드가 보이는지 확인합니다.

```bash
arecord -l
```

정상 예:

```text
card 2: seeed2micvoicec [seeed2micvoicec], device 0: bcm2835-i2s-tlv320aic3x-hifi ...
```

카드 번호는 부팅 상태에 따라 달라질 수 있습니다. 코드는 카드 번호 대신 `CARD=seeed2micvoicec` 이름을 사용합니다.

3. 녹음 시간이 정상인지 확인합니다.

```bash
time arecord -q -D plughw:CARD=seeed2micvoicec,DEV=0 -f S16_LE -r 16000 -c 2 -d 5 test.wav
```

정상:

```text
real    0m5.xxxs
```

비정상:

```text
overrun!!!
real    0m0.1xxs
```

비정상이면 I2S 캡처가 깨진 상태입니다. 대부분 `sudo pigpiod`를 기본 옵션으로 실행했거나, ReSpeaker overlay/clock이 꼬인 상태입니다.

## 실행

```bash
cd ~/Documents/SLM_Control
export GOOGLE_APPLICATION_CREDENTIALS=/home/pi/Documents/SLM_Control/google-stt-key.json
sudo pigpiod -t 0
python3 main.py
```

`main.py`는 다음 프로세스를 관리합니다.

- `stt.py`
- `servo_control.py`
- `parsing.py`

중간에 `Ctrl+C`를 눌러도 `main.py`가 자식 프로세스 그룹을 정리합니다. `stt.py` 내부의 `arecord`도 별도 프로세스 그룹으로 실행되어 종료 시 함께 정리됩니다.

## STT

현재 `stt.py`는 Google Cloud Speech-to-Text API를 사용합니다.

```python
speech_client = speech.SpeechClient()
response = speech_client.recognize(
    config=recognition_config,
    audio=audio,
)
```

인식 설정:

```python
language_code = "ko-KR"
sample_rate_hertz = 16000
audio_channel_count = 2
```

Google 인증이 안 되어 있으면 `stt.py` 시작 시 클라이언트 초기화 단계에서 실패합니다.

## Qwen 명령 분류

`parsing.py`는 STT 결과를 받아 `qwen.py`의 Qwen3-0.6B 분류기로 넘깁니다.

현재 분류 라벨:

- `LIGHT_ON`: `{"action": 1}`
- `LIGHT_OFF`: `{"action": -1}`
- `OTHER`: `{"action": 0}`

`servo_control.py`는 `action` 값에 따라 GPIO 12의 서보 각도를 바꿉니다.

## 문제 해결

### `Can't lock /var/run/pigpio.pid`

이미 `pigpiod`가 떠 있을 때 다시 실행하면 나옵니다.

```bash
pgrep -af pigpiod
```

`pigpiod -t 0`이면 정상입니다.

### `arecord`가 5초를 못 채우고 바로 끝남

예:

```text
overrun!!!
real    0m0.103s
```

I2S 캡처가 깨진 상태입니다.

1. `pigpiod`를 기본 옵션으로 실행하지 않았는지 확인
2. `pgrep -af pigpiod`가 `pigpiod -t 0`인지 확인
3. 그래도 깨져 있으면 재부팅

```bash
sudo reboot
```

`stt.py`는 이 상황을 감지하면 Google STT 요청을 진행하지 않고 다음 메시지를 출력한 뒤 종료합니다.

```text
I2S 캡처가 비정상입니다.
sudo reboot 후 다시 실행하세요.
```

### 녹음은 되는데 소음만 들어감

ReSpeaker v2 overlay는 `LINE1L/LINE1R` 입력을 사용합니다. 현재 권장 mixer 설정:

```bash
amixer -c 2 sset 'Left PGA Mixer Mic2L' off
amixer -c 2 sset 'Right PGA Mixer Mic2R' off
amixer -c 2 sset 'Left PGA Mixer Line1L' on
amixer -c 2 sset 'Right PGA Mixer Line1R' on
amixer -c 2 sset 'AGC' off
amixer -c 2 sset 'PGA' 32
sudo alsactl store
```

카드 번호가 다르면 `-c 2` 대신 실제 카드 번호를 사용하세요.

### Google 인증 실패

예:

```text
Google Cloud STT 클라이언트 초기화 실패
```

확인:

```bash
echo $GOOGLE_APPLICATION_CREDENTIALS
ls -l "$GOOGLE_APPLICATION_CREDENTIALS"
```

설정:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/home/pi/Documents/SLM_Control/google-stt-key.json
```

재부팅 후에는 다시 export해야 합니다. 계속 유지하려면 `~/.bashrc`에 넣으세요.

### 실행 후 프로세스가 남았는지 확인

```bash
pgrep -af 'main.py|stt.py|parsing.py|servo_control.py|arecord'
```

아무것도 안 나오면 정상 종료입니다. `grep`만 보이는 것은 실행 중인 프로세스가 아닙니다.

## 참고

- ReSpeaker 2-Mics Pi HAT v2 공식 문서: https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/
- pigpio daemon help:

```bash
pigpiod -?
```
