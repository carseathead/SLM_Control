import socket
import sys

print("┌────────────────────────────────────────────────────────┐")
print("│      [Client] STT 엔진 서버(Port: 12345)에 접속합니다...     │")
print("└────────────────────────────────────────────────────────┘")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client_socket.connect(('localhost', 12345))
    print("✅ STT 엔진에 실시간 링크 연동 완료!")
    print("📥 음성 명령 수신 대기 중...\n")
except ConnectionRefusedError:
    print("❌ 접속 실패! stt_engine.py 파일을 터미널에서 먼저 실행해 주세요.")
    sys.exit(1)

try:
    buffer = ""
    while True:
        # STT 서버로부터 데이터 수신
        data = client_socket.recv(1024)
        if not data:
            print("🛑 STT 엔진 서버가 종료되었습니다.")
            break
            
        # 데이터를 문자열로 디코딩 후 줄바꿈 단위로 처리
        buffer += data.decode('utf-8')
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            command = line.strip()
            
            if command:
                print(f"📥 [수신된 음성 명령]: \"{command}\"")
                
                # ===================================================
                # 여기서부터 수신된 텍스트로 원하는 알고리즘/구동 코드를 구현합니다.
                # ===================================================
                if "불" in command and "켜" in command:
                    print("▶️ [동작 실행] 💡 스마트 전등(GPIO)을 점등합니다.")
                elif "불" in command and "끄" in command:
                    print("▶️ [동작 실행] 🌑 스마트 전등(GPIO)을 소등합니다.")
                elif "정지" in command or "스톱" in command:
                    print("▶️ [동작 실행] 🛑 모터 구동을 즉시 정지합니다.")
                elif "종료" in command:
                    print("▶️ [동작 실행] 프로그램을 안전하게 완전 종료합니다.")
                    raise KeyboardInterrupt
                # ===================================================

except KeyboardInterrupt:
    print("\n👋 제어 프로그램을 정지합니다.")
finally:
    client_socket.close() 