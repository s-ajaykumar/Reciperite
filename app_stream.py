import prompts
from dotenv import load_dotenv
from google import genai
from google.genai import types
import websockets
import asyncio

load_dotenv()

user_details = {'name': 'ajay'}

MODEL = "models/gemini-2.0-flash-live-001"
TEXT_CONFIG = {"system_instruction": prompts.instruction2.format(user_details = user_details), "response_modalities": ["TEXT"]}
AUDIO_CONFIG = {"system_instruction": prompts.instruction2.format(user_details = user_details), "response_modalities": ["AUDIO"]}

client = genai.Client(http_options={"api_version": "v1beta"})

class WebSocketServer:
    def __init__(self):
        self.stt_ws = None
        self.audio_ws = None
        self.audio_in_queue = None
        self.audio_out_queue = None
        self.text_queue = None
        self.text_queue2 = None
        self.client = None
        
    async def receive_client_audio(self, stream):
        self.audio_ws = stream

        async for chunk in stream:
            await self.audio_in_queue.put(chunk)
     
    async def send_audio(self):
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                audio_data = {'data' : chunk, 'mime_type' : 'audio/pcm'}
                await self.stt_ws.send(input = audio_data)
                    
        except asyncio.CancelledError:
            raise asyncio.CancelledError("User requested exit")
            
    async def receive_text(self):
        while True:
            turn = self.stt_ws.receive()
            async for data in turn:
                await self.text_queue.put(data.text)
                await self.text_queue2.put(data.text)
                print(data.text)
        
    async def send_text(self):
        while True:
            text = await self.text_queue2.get()
            text_data = {'text': text, 'mime_type': 'text/plain'}
            await self.tts_ws.send(input=text_data)
        
    async def receive_ai_audio(self):
        while True:
            turn = self.tts_ws.receive()
            async for response in turn:
                self.audio_out_queue.put_nowait(response.data)
    
    async def send_audio_to_client(self):
        while True:
            audio_data = await self.audio_out_queue.get()
            await self.audio_ws.send(audio_data)
    
    async def main(self):
        try:
            async with client.aio.live.connect(model=MODEL, config=TEXT_CONFIG) as stt_ws:
                
                self.stt_ws = stt_ws
                self.audio_in_queue = asyncio.Queue()
                self.audio_out_queue = asyncio.Queue()
                self.text_queue = asyncio.Queue()
                self.text_queue2 = asyncio.Queue()
                
                asyncio.create_task(self.send_audio())
                asyncio.create_task(self.receive_text())
        
                async with client.aio.live.connect(model=MODEL, config=AUDIO_CONFIG) as tts_ws:
                    self.tts_ws = tts_ws
                    asyncio.create_task(self.send_text())
                    asyncio.create_task(self.receive_ai_audio())
                    asyncio.create_task(self.send_audio_to_client())
                
                    async with websockets.serve(self.receive_client_audio, 'localhost', 8000) as audio_ws:
                        print("server running on ws://localhost:8000")
                        await asyncio.Future()
                    
        except Exception as e:
            print(f"An error occurred: {e}")
 
 
if __name__ == "__main__": 
     server = WebSocketServer()
     asyncio.run(server.main())   
        
