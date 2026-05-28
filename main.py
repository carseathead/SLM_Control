import os
import signal
import subprocess
import sys
import time


SHUTDOWN_TIMEOUT = 5


def start_child(script_name):
    return subprocess.Popen(
        [sys.executable, script_name],
        stdout=None,
        stderr=None,
        start_new_session=True,
    )


def stop_child(name, process):
    if process is None or process.poll() is not None:
        return

    print(f"🧹 [Main] {name} 종료 신호 전송...")
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=SHUTDOWN_TIMEOUT)
        return
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        print(f"⚠️ [Main] {name}가 종료되지 않아 강제 종료합니다.")

    try:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2)
    except ProcessLookupError:
        pass


def wait_for_startup(processes, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for name, process in processes:
            if process is not None and process.poll() is not None:
                raise RuntimeError(f"{name} 프로세스가 시작 대기 중 종료되었습니다. exit={process.returncode}")
        time.sleep(0.2)


def main():
    print("🚀 [Main] 온디바이스 멀티프로세스 제어 시스템을 가동합니다.")

    stt_process = None
    servo_process = None
    parsing_process = None

    try:
        stt_process = start_child("stt.py")
        servo_process = start_child("servo_control.py")

        print("⏳ [Main] STT/VLM 모델 로드 및 소켓 네트워크 빌드업 대기 중 (10초)...")
        wait_for_startup(
            [
                ("STT", stt_process),
                ("Servo", servo_process),
            ],
            10,
        )

        print("💡 [Main] 중앙 파싱(Parsing) 노드 시퀀스를 시작합니다.")
        parsing_process = start_child("parsing.py")
        parsing_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 [Main] 사용자가 메인 시스템을 강제 종료했습니다.")
    except RuntimeError as e:
        print(f"❌ [Main] 시작 실패: {e}")
    finally:
        print("🧹 [Main] 백그라운드 프로세스들을 정리합니다.")
        stop_child("Parsing", parsing_process)
        stop_child("STT", stt_process)
        stop_child("Servo", servo_process)
        print("✨ [Main] 모든 서브 시스템이 안전하게 전원 차단되었습니다.")


if __name__ == "__main__":
    main()
