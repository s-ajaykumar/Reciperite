import data.prompts as prompts
from dotenv import load_dotenv
from google import genai
from google.genai import types
import websockets
import asyncio
import time
from deepgram.utils import verboselogs
from deepgram import (
    DeepgramClient,
    SpeakWebSocketEvents,
    SpeakWSOptions,
)

load_dotenv()


user_details = {'name': 'ajay'}

STT_MODEL = "models/gemini-2.0-flash-live-001"
STT_CONFIG = types.LiveConnectConfig(
    response_modalities=[
        "TEXT",
    ],
    system_instruction=types.Content(
        parts=[types.Part.from_text(text=prompts.instruction2.format(user_details = user_details))],
        role="user"
    ),
)

client = genai.Client(http_options={"api_version": "v1beta"})
deepgram: DeepgramClient = DeepgramClient()



def on_binary_data(self, data, **kwargs):
    server.audio_out_queue.put_nowait(data)
   
    
    
class Server:
    def __init__(self):
        self.stt_ws = None
        self.audio_ws = None
        self.audio_in_queue = None
        self.audio_out_queue = None
        self.text_queue = None
        
    async def receive_client_audio(self, websocket):
        self.audio_ws = websocket

        async for chunk in self.audio_ws:
            await self.audio_in_queue.put(chunk)
     
    async def send_audio(self):
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                audio_data = {'data' : chunk, 'mime_type' : 'audio/pcm'}
                await self.stt_ws.send(input = audio_data)
                    
        except Exception as e:
            print(f"An error occurred while sending audio to STT WebSocket: {e}")
            
    async def receive_text(self):
        try:
            while True:
                turn = self.stt_ws.receive()
                async for response in turn:
                    if text := response.text:
                        if response.server_content.interrupted is True:
                            await self.audio_ws.send("Interrupted")
                            print("Turn end")
                            while not self.text_queue.empty():
                                await self.text_queue.get_nowait()
                            continue
                        
                        await self.text_queue.put(text)
                        print(text)
                    else:
                        await self.text_queue.put("Turn end")
                    
        except websockets.exceptions.ConnectionClosedOK:
            print("STT WebSocket connection closed gracefully.")
            
        except Exception as e:
            print(f"Error receiving text from STT WebSocket: {e}")
        
    async def tts(self):
        try:
            while True:
                text = await self.text_queue.get()
                if text != "Turn end":
                    self.dg_connection.send_text(text)
                else:
                    self.dg_connection.flush()
                    
        except Exception as e:
            print(f"An error occurred in deepgram api: {e}")
                
    async def send_audio_to_client(self):
        while True:
            audio_data = await self.audio_out_queue.get()
            await self.audio_ws.send(audio_data)
        
    async def main(self):
        self.audio_in_queue = asyncio.Queue(maxsize = 100)
        self.audio_out_queue = asyncio.Queue(maxsize = 100)
        self.text_queue = asyncio.Queue(maxsize = 50)
        
        try:
            async with client.aio.live.connect(model=STT_MODEL, config = STT_CONFIG) as stt_ws:
                self.stt_ws = stt_ws
                
                self.dg_connection = deepgram.speak.websocket.v("1")
                self.dg_connection.on(SpeakWebSocketEvents.AudioData, on_binary_data)
                options = SpeakWSOptions(
                    model="aura-2-thalia-en",
                    encoding="linear16",
                    sample_rate=16000,
                )
                if self.dg_connection.start(options) is False:
                    print("Failed to start connection")
                    return
                
                asyncio.create_task(self.send_audio())
                asyncio.create_task(self.receive_text())
                asyncio.create_task(self.tts())
                asyncio.create_task(self.send_audio_to_client())
                
                async with websockets.serve(self.receive_client_audio, 'localhost', 8000):
                    print("server running on ws://localhost:8000")
                    await asyncio.Future()
                    
                    
        except websockets.exceptions.ConnectionClosedOK:
            print("WebSocket connection closed gracefully.")
                    
        except asyncio.CancelledError:
            pass
 
 
 
if __name__ == "__main__": 
     server = Server()
     asyncio.run(server.main())   
        
