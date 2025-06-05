import nemo.collections.asr as nemo_asr
import time


asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v2")

t1 = time.time()
output = asr_model.transcribe(['2086-149220-0033.wav'])
t2 = time.time()
print(f"Time taken for STT: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
print(output[0].text)
