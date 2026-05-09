import qwen
import psutil
import os


qwenllm = qwen.Qwen()
print(qwenllm("불 켜 줘"))
process = psutil.Process(os.getpid())
print(f"메모리 사용량: {process.memory_info().rss / (1024 * 1024):.2f} MB")