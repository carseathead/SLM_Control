import socket
import json
import sys
import pigpio

SERVO_PIN = 12

# pigpio 초기화
pi = pigpio.pi()
if not pi.connected:
    print("❌ [Servo] pigpio 데몬이 실행되지 않았습니다.")
    print("   ReSpeaker I2S와 충돌하므로 'sudo pigpiod'가 아니라 'sudo pigpiod -t 0'로 실행하세요.")
    sys.exit(1)

def set_servo_angle(angle):
    pulse_width = 500 + (angle / 180.0) * 1500
    pi.set_servo_pulsewidth(SERVO_PIN, pulse_width)
    print(f"📐 [Servo] 각도 이동 완료: {angle}도")

# parsing.py의 데이터를 받기 위한 소켓 서버 개설 (12346 포트)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('localhost', 12346))
server_socket.listen(1)
server_socket.settimeout(1.0)

print("⚙️ [Servo] 모터 제어 노드가 가동되었습니다. 파싱 노드의 연결을 대기합니다...")
while True:
    try:
        client_socket, addr = server_socket.accept()
        break
    except socket.timeout:
        continue
print(f"🔗 [Servo] 파싱 노드 연결 성공: {addr}")

try:
    buffer = ""
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
            
        buffer += data.decode('utf-8')
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if not line.strip(): continue
            
            try:
                # 수신된 문자열을 JSON 데이터로 파싱
                command_data = json.loads(line.strip())
                action = command_data.get("action", 0)
                print(f"📥 [Servo] 명령 캐치 -> action: {action}")
                
                # 조건에 따른 각도 제어
                if action == 1:
                    set_servo_angle(0)
                elif action == -1:
                    set_servo_angle(180)
                elif action == 0:
                    print("💤 [Servo] action이 0이므로 대기합니다.")
                    
            except json.JSONDecodeError:
                print(f"⚠️ [Servo] 잘못된 JSON 포맷 수신: {line}")

except KeyboardInterrupt:
    print("\n🛑 [Servo] 모터 제어 프로그램을 종료합니다.")
finally:
    pi.set_servo_pulsewidth(SERVO_PIN, 0)
    pi.stop()
    client_socket.close()
    server_socket.close()
