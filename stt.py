import os
import signal
import sys
import socket
import subprocess
import time

VENV_SITE_PACKAGES = os.path.join(
    os.path.dirname(__file__),
    "venv",
    "lib",
    f"python{sys.version_info.major}.{sys.version_info.minor}",
    "site-packages",
)
if os.path.isdir(VENV_SITE_PACKAGES) and VENV_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, VENV_SITE_PACKAGES)

from google.api_core.exceptions import GoogleAPIError
from google.cloud import speech

# 1. reSpeaker 2-Mics 하드웨어 칩셋 고정 포맷 설정
CHANNELS = 2               # ReSpeaker 2-Mics Pi HAT v2 캡처 채널
RATE = 16000               # 음성 인식용 샘플링 레이트
RECORD_SECONDS = 2         # 명령 제어용 지연을 줄이기 위한 짧은 녹음 단위
ALSA_DEVICE = "plughw:CARD=seeed2micvoicec,DEV=0"
ARECORD_TIMEOUT = 8
TEMP_FILENAME = "stream_chunk.wav"
LANGUAGE_CODE = "ko-KR"
MIN_RECORD_RATIO = 0.7

# 2. 내부 소켓 서버 개설
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('localhost', 12345))
server_socket.listen(1)
server_socket.settimeout(1.0)

print("┌────────────────────────────────────────────────────────┐")
print("│  [Socket Server] 제어 구동 파일(Client) 연결을 대기합니다... │")
print("└────────────────────────────────────────────────────────┘")
while True:
    try:
        client_socket, addr = server_socket.accept()
        break
    except socket.timeout:
        continue
print(f"🔗 제어 프로그램 연결 성공! (연결 주소: {addr})")

# 3. Google Cloud Speech-to-Text 클라이언트 준비
print("\n💡 Google Cloud STT 클라이언트 초기화 중...")
try:
    speech_client = speech.SpeechClient()
except Exception as e:
    print(f"❌ Google Cloud STT 클라이언트 초기화 실패: {e}")
    print("   확인: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json")
    client_socket.close()
    server_socket.close()
    sys.exit(1)

recognition_config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=RATE,
    language_code=LANGUAGE_CODE,
    audio_channel_count=CHANNELS,
    enable_automatic_punctuation=False,
)
print("✅ Google Cloud STT 준비 완료.")

print(f"🔌 [STT] ALSA 입력 장치 사용: {ALSA_DEVICE}")
print("\n🚀 실시간 STT 엔진 구동 시작! 마이크에 대고 말씀하세요... (Ctrl+C 종료)")

arecord_process = None

try:
    while True:
        record_cmd = [
            "arecord",
            "-q",
            "-D", ALSA_DEVICE,
            "-f", "S16_LE",
            "-r", str(RATE),
            "-c", str(CHANNELS),
            "-d", str(RECORD_SECONDS),
            TEMP_FILENAME,
        ]

        try:
            arecord_process = subprocess.Popen(
                record_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            record_started_at = time.monotonic()
            stdout_text, stderr_text = arecord_process.communicate(timeout=ARECORD_TIMEOUT)
            record_elapsed = time.monotonic() - record_started_at
            arecord_returncode = arecord_process.returncode
        except subprocess.TimeoutExpired:
            print(f"❌ [STT] arecord가 시간 초과로 중단되었습니다: {ALSA_DEVICE}")
            if arecord_process is not None:
                try:
                    os.killpg(arecord_process.pid, signal.SIGTERM)
                    arecord_process.wait(timeout=2)
                except Exception:
                    try:
                        os.killpg(arecord_process.pid, signal.SIGKILL)
                    except Exception:
                        pass
            client_socket.sendall("[BLANK_AUDIO]\n".encode('utf-8'))
            continue
        finally:
            arecord_process = None

        if arecord_returncode != 0 or not os.path.exists(TEMP_FILENAME) or os.path.getsize(TEMP_FILENAME) <= 44:
            print(f"❌ [STT] arecord 녹음 실패: {stderr_text.strip()}")
            print(f"   현재 ALSA 장치: {ALSA_DEVICE}")
            print("   먼저 확인: arecord -D plughw:CARD=seeed2micvoicec,DEV=0 -f S16_LE -r 16000 -c 2 -d 3 test.wav")
            client_socket.sendall("[BLANK_AUDIO]\n".encode('utf-8'))
            continue

        if record_elapsed < RECORD_SECONDS * MIN_RECORD_RATIO:
            print(
                "❌ [STT] I2S 캡처가 비정상입니다. "
                f"{RECORD_SECONDS}초 녹음이 {record_elapsed:.2f}초 만에 종료되었습니다."
            )
            print("   ReSpeaker 드라이버 스트림이 깨진 상태일 수 있습니다. sudo reboot 후 다시 실행하세요.")
            client_socket.sendall("[BLANK_AUDIO]\n".encode('utf-8'))
            break

        print(f"📊 [STT] {RECORD_SECONDS}초 음성 버퍼 수집 완료 -> Google STT 요청 시작...")

        try:
            with open(TEMP_FILENAME, "rb") as audio_file:
                audio = speech.RecognitionAudio(content=audio_file.read())

            response = speech_client.recognize(
                config=recognition_config,
                audio=audio,
            )
        except GoogleAPIError as e:
            print(f"❌ [STT] Google STT API 오류: {e}")
            client_socket.sendall("[BLANK_AUDIO]\n".encode('utf-8'))
            continue
        except Exception as e:
            print(f"❌ [STT] 음성 인식 처리 실패: {e}")
            client_socket.sendall("[BLANK_AUDIO]\n".encode('utf-8'))
            continue

        transcripts = []
        for result in response.results:
            if result.alternatives:
                transcript = result.alternatives[0].transcript.strip()
                if transcript:
                    transcripts.append(transcript)

        text = " ".join(transcripts).strip()
        has_text = len(text) > 1
        if has_text:
            print(f"🎤 [실시간 인식 결과]: {text}")
            try:
                client_socket.sendall(f"{text}\n".encode('utf-8'))
            except BrokenPipeError:
                break
                    
        # 무음 구간일 때도 루프가 도는 것을 시각적으로 확인하기 위함
        if not has_text:
            print("💤 [STT] 무음 구간 (대기 중)")
            client_socket.sendall("[BLANK_AUDIO]\n".encode('utf-8'))
                    
except KeyboardInterrupt:
    print("\n🛑 사용자에 의해 STT 엔진을 종료합니다.")
finally:
    if arecord_process is not None and arecord_process.poll() is None:
        try:
            os.killpg(arecord_process.pid, signal.SIGTERM)
            arecord_process.wait(timeout=2)
        except Exception:
            try:
                os.killpg(arecord_process.pid, signal.SIGKILL)
            except Exception:
                pass
    client_socket.close()
    server_socket.close()
    if os.path.exists(TEMP_FILENAME):
        os.remove(TEMP_FILENAME)
