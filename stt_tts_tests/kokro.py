from kokoro import KPipeline
import websockets
import asyncio
import pyaudio
import numpy as np

pipeline = KPipeline(lang_code='a')
pa = pyaudio.PyAudio()

class TTS:
    def __init__(self):
        self.text_in_queue = None
        self.audio_out_queue = None

    async def receive_text(self, ws):
        async for text in ws:
            await self.text_in_queue.put(text)

    async def tts(self):
        while True:
            text = await self.text_in_queue.get()
            generator = pipeline(
                text, voice='af_sky', # <= change voice here
                speed=1, split_pattern=r'\n+'
            )
            for i, (gs, ps, audio) in enumerate(generator):
                # i => index    gs => graphemes/text    s => phonemes
                try:
                    audio_np = audio.detach().cpu().numpy() # Detach from graph, move to CPU, convert to NumPy
                    
                except AttributeError:
                    print("it is not a torch tensor")
                  
                audio_bytes = audio_np.tobytes()
                  
                self.audio_out_queue.put_nowait(audio_bytes) 
            
    async def play_audio(self):
        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=24000,
            output=True
        )
        while True:
            audio = await self.audio_out_queue.get()
            stream.write(audio)

    async def main(self):
        async with websockets.serve(self.receive_text, 'localhost', 8765):
            print("WebSocket server started on ws://localhost:8765")
            self.text_in_queue = asyncio.Queue(maxsize = 50)
            self.audio_out_queue = asyncio.Queue(maxsize = 100)
            
            asyncio.create_task(self.tts())
            asyncio.create_task(self.play_audio())
            
            await asyncio.Future()
 
if __name__ == '__main__':           
    tts = TTS()
    asyncio.run(tts.main())
