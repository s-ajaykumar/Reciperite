from whisper import load_model
import time

# Load Whisper model
model = load_model("base")

t1 = time.time()
result = model.transcribe("2086-149220-0033.wav")
t2 = time.time()

print(f"Time taken for STT: {t2-t1:.3f}sec {(t2 - t1)*1000:.4f} ms")
print(result["text"])