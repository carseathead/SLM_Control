import os
import sys
import socket
import pyaudio
import wave
from pywhispercpp.model import Model
import psutil
# 1. 마이크 장치 및 오디오 포맷 설정
FORMAT = pyaudio.paInt16
CHANNELS = 2               # reSpeaker 2-Mics 기본 채널
RATE = 16000               # Whisper 권장 샘플링 레이트
CHUNK = 1024
RECORD_SECONDS = 10         # 10초 단위로 음성을 끊어서 추론
INPUT_DEVICE_INDEX = 3     # 아까 확인한 card 3 번호 세팅!
TEMP_FILENAME = "stream_chunk.wav"

# 2. 내부 소켓 서버 개설 (제어부 파이썬 파일과 통신용)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('localhost', 12345))
server_socket.listen(1)

print("┌────────────────────────────────────────────────────────┐")
print("│  [Socket Server] 제어 구동 파일(Client) 연결을 대기합니다... │")
print("└────────────────────────────────────────────────────────┘")
client_socket, addr = server_socket.accept()
print(f"🔗 제어 프로그램 연결 성공! (연결 주소: {addr})")

# 3. 500MB 이내 경량 Whisper 'tiny' 한국어 모델 로드
print("\n💡 Whisper 온디바이스 경량 모델(tiny) 로딩 중...")
model = Model('tiny')
print("✅ 모델 로드 완료. (RAM 사용량 약 200MB 이내)")

p = pyaudio.PyAudio()

try:
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=INPUT_DEVICE_INDEX, # 마이크 장치 명시
        frames_per_buffer=CHUNK
    )
except Exception as e:
    print(f"❌ 마이크 개방 실패! 장치 번호를 확인하세요. 에러: {e}")
    client_socket.close()
    server_socket.close()
    sys.exit(1)

print("\n🚀 실시간 STT 엔진 구동 시작! 마이크에 대고 말씀하세요... (Ctrl+C 종료)")

try:
    while True:
        frames = []
        # 3초 동안의 오디오 조각 수집
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
        # 추론을 위해 임시 WAV 파일로 임베딩 저장
        wf = wave.open(TEMP_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        # Whisper 로컬 온디바이스 STT 실행 (외부 인터넷/API 미사용)
        segments = model.transcribe(TEMP_FILENAME)
        
        for segment in segments:
            text = segment.text.strip()
            if text and len(text) > 1: # 의미 없는 한 글자 가짜 노이즈 필터링
                print(f"🎤 [실시간 인식] {text}")
                process = psutil.Process(os.getpid())
                print(f"📊 현재 메모리 사용량: {process.memory_info().rss / (1024 * 1024):.2f} MB")
                # 4. 수신 측 파이썬 파일로 텍스트 데이터 전송
                try:
                    client_socket.sendall(f"{text}\n".encode('utf-8'))
                except BrokenPipeError:
                    print("⚠️ 수신 측 파이썬 파일과의 연결이 끊겼습니다.")
                    break
                    
except KeyboardInterrupt:
    print("\n🛑 사용자에 의해 STT 엔진을 종료합니다.")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()
    client_socket.close()
    server_socket.close()
    if os.path.exists(TEMP_FILENAME):
        os.remove(TEMP_FILENAME)