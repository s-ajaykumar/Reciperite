import asyncio
import websockets 
import pyaudio
import json
import base64

CHANNEL = 1
FORMAT = pyaudio.paInt16
IN_RATE = 16000
OUT_RATE = 16000
CHUNK = 1024

pya  = pyaudio.PyAudio()

class AudioClient:
    def __init__(self):
        self.ws = None
        self.audio_in_queue = None
        self.audio_out_queue = None

    async def receive_audio(self):
        while True:
            data = await self.ws.recv()
            data = json.loads(data)
            
            if data['type'] == "control_msg":
                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
                    
            elif data['type'] == "recipe_audio" or data['type'] == "unrelated":
                audio_bytes = base64.b64decode(data['data'])
                self.audio_in_queue.put_nowait(audio_bytes)
                
            elif data['type'] == 'ai_text_response':
                print("AI text response:\n", data['data'], "\n\n")
    
    async def play_audio(self):
        speaker = await asyncio.to_thread(pya.open,
            format=FORMAT,
            channels=CHANNEL,
            rate=OUT_RATE,
            output=True
        )
        
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                await asyncio.to_thread(speaker.write, chunk)
        except Exception as e:
            print(f"An error occurred while playing audio: {e}")
        finally:
            speaker.close()
            speaker.terminate()
     
    async def send_audio(self):
        try:
            while True:
                chunk = await self.audio_out_queue.get()   
                await self.ws.send(chunk)
                
        except Exception as e:
            print(f"An error occurred while sending audio: {e}")
     
    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        mic = await asyncio.to_thread(pya.open,
                format=FORMAT,
                channels=CHANNEL,
                rate=IN_RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index = mic_info['index']
            )
        try:
            if __debug__:
                kwargs = {"exception_on_overflow": False}
            else:
                kwargs = {}
            while True:
                chunk = await asyncio.to_thread(mic.read, CHUNK, **kwargs)
                await self.audio_out_queue.put(chunk)
                
        except Exception as e:
            print(f"An error occurred while listening audio: {e}")
            
        finally:
            mic.close()
                              
    async def main(self):
        try:
            async with websockets.connect("wss://promoted-solid-gannet.ngrok-free.app") as ws:
                print("websocket connected to wss://promoted-solid-gannet.ngrok-free.app")
                self.ws = ws
                self.audio_in_queue = asyncio.Queue(maxsize = 100)
                self.audio_out_queue = asyncio.Queue(maxsize = 100)
                
                asyncio.create_task(self.listen_audio())
                asyncio.create_task(self.send_audio())
                asyncio.create_task(self.receive_audio())
                asyncio.create_task(self.play_audio())
                
                await asyncio.Future()
                
        except Exception as e:
            print(f"An error occurred: {e}")
            
if __name__ == '__main__':
    audio_client = AudioClient()
    asyncio.run(audio_client.main())