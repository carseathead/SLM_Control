import qwen
import psutil
import os
import socket
import sys
import json
import time  # 💡 time.sleep 사용을 위해 임포트 추가

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

servo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("⏳ [Parsing] 서보 제어 서버 연결 시도 중...")
while True:
    try:
        servo_socket.connect(('localhost', 12346))
        print("✅ [Parsing] 서보 제어 노드 연동 성공!")
        break
    except ConnectionRefusedError:
        time.sleep(0.5)  # 서보 파일이 켜질 때까지 잠깐 대기

qwenllm = qwen.Qwen()

try:
    buffer = ""
    while True:
        # STT 서버로부터 실시간 음성 텍스트 수신
        buffer = ""
        data = client_socket.recv(1024)
        if not data:
            print("🛑 STT 엔진 서버가 종료되었습니다.")
            break
            
        # 데이터를 문자열로 디코딩 후 누적
        buffer += data.decode('utf-8')
        print(f"📥 [수신된 데이터 조각]: {buffer.strip()}")  # 수신된 데이터 조각 로그 출력
        # 💡 스트리밍 데이터 유실 방지를 위해 줄바꿈(\n) 단위로 한 줄씩 잘라서 처리
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            voice_text = line.strip()
            
            if not voice_text:
                continue
                
            if voice_text == "[BLANK_AUDIO]":
                print("⚠️  인식된 음성 명령이 없습니다. (무음 구간)")
                continue
                
            print(f"📥 [수신된 음성 명령]: {voice_text}")
            
            # 1. Qwen LLM 가동 (입력된 한글 문장을 분석해 딕셔너리 혹은 JSON 스트링 반환)
            qwen_response = qwenllm(voice_text)
            print(f"🤖 [Qwen 분석 결과]: {qwen_response}")
            
            # 2. Qwen의 리턴 형태가 '문자열'이든 '딕셔너리'든 상관없이 완벽하게 처리하기
            try:
                if isinstance(qwen_response, str):
                    # 만약 문자열(String) 형태라면 형식이 올바른지 JSON으로 파싱 검증
                    command_dict = json.loads(qwen_response)
                else:
                    # 이미 딕셔너리(Dict) 객체라면 그대로 할당
                    command_dict = qwen_response
                
                # 3. 획득한 JSON 데이터를 한 줄짜리 문자열로 직렬화(변환)
                # 수신 측(servo_control.py)에서 readline()으로 끊어 읽을 수 있게 맨 뒤에 '\n' 부착
                json_message = json.dumps(command_dict) + "\n"
                
                # 4. 서보 모터 제어 노드로 전송
                servo_socket.sendall(json_message.encode('utf-8'))
                print(f"✈️  [Parsing -> Servo] 명령 전송 완료: {json_message.strip()}")
                
            except Exception as e:
                print(f"⚠️ [Parsing] Qwen 응답을 JSON으로 변환하거나 전송하는 데 실패했습니다. 에러: {e}")

except KeyboardInterrupt:
    print("\n👋 제어 프로그램을 정지합니다.")
finally:
    client_socket.close() 
    servo_socket.close()