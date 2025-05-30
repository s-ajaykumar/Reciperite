import asyncio
import websockets 
import pyaudio

CHANNEL = 1
FORMAT = pyaudio.paInt16
RATE = 24000
OUT_RATE = 16000
CHUNK = 1024


class AudioClient:
    def __init__(self):
        self.ws = None
        self.response_queue = None

    async def receive_audio(self):
        while True:
            data = await self.ws.recv()
            self.response_queue.put_nowait(data)
    
    async def play_audio(self):
        speaker = pyaudio.PyAudio()
        stream = speaker.open(
            format=FORMAT,
            channels=CHANNEL,
            rate=OUT_RATE,
            output=True,
            frames_per_buffer=CHUNK
        )
        
        try:
            while True:
                chunk = await self.response_queue.get()
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"An error occurred while playing audio: {e}")
        finally:
            stream.close()
            stream.terminate()
     
    async def send_audio(self): 
        p = pyaudio.PyAudio()
        mic = p.open(
                format=FORMAT,
                channels=CHANNEL,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
        try:
            while True:
                chunk = await asyncio.to_thread(mic.read, CHUNK)
                await self.ws.send(chunk)
        except Exception as e:
            print(f"An error occurred while sending audio: {e}")
        finally:
            mic.close()
            p.terminate()
                              
    async def main(self):
        try:
            async with websockets.connect("ws://localhost:8000") as ws:
                self.ws = ws
                self.response_queue = asyncio.Queue()
                
                asyncio.create_task(self.send_audio())
                asyncio.create_task(self.receive_audio())
                asyncio.create_task(self.play_audio())
                await asyncio.Future()
                
        except Exception as e:
            print(f"An error occurred: {e}")
            
if __name__ == '__main__':
    audio_client = AudioClient()
    asyncio.run(audio_client.main())