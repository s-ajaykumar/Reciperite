import prompts
from dotenv import load_dotenv
import time
import json

import websockets
import asyncio

from google import genai
from google.genai import types

from deepgram.utils import verboselogs
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    SpeakWebSocketEvents,
    SpeakWSOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

load_dotenv()


user_details = {'name': 'ajay'}

TTT_MODEL = "gemini-2.5-flash-preview-05-20"
TTT_CONFIG = types.GenerateContentConfig(
    temperature=0,
    thinking_config = types.ThinkingConfig(
        thinking_budget=0,
    ),
    response_mime_type="application/json",
)
gemini = genai.Client()

config: DeepgramClientOptions = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
deepgram: DeepgramClient = DeepgramClient("", config)


is_finals = []
async def receive_stt_text(self, result, **kwargs):
    global is_finals
    sentence = result.channel.alternatives[0].transcript
    if len(sentence) == 0:
        return
    if result.is_final:
        is_finals.append(sentence)
        
        if result.speech_final:
            utterance = " ".join(is_finals)
            await server.text_in_queue.put(utterance)
            print(f"STT: {utterance}")
            is_finals = []
    
async def on_utterance_end(self, utterance_end, **kwargs):
    print("Utterance End")
    global is_finals
    if len(is_finals) > 0:
        utterance = " ".join(is_finals)
        await server.text_in_queue.put(utterance)
        print(f"Utterance End: {utterance}")
        is_finals = []  
                  
def receive_tts_audio(self, data, **kwargs):
    server.audio_out_queue.put_nowait(data)
  
    
class Server:
    def __init__(self):
        self.client_ws = None
        self.audio_in_queue = None
        self.audio_out_queue = None
        self.text_in_queue = None
        self.text_out_queue = None
        
    async def receive_client_audio(self, websocket):
        self.client_ws = websocket
        async for chunk in self.client_ws:
            await self.audio_in_queue.put(chunk)
     
    async def stt(self):
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                await self.stt_connection.send(chunk)
                    
        except Exception as e:
            print(f"An error occurred while sending audio to STT client: {e}")
              
    async def ttt(self):
        try:
            while True:
                text = await self.text_in_queue.get()
                if text:
                    print("Performing TTT...")            
                    t1 = time.time()
                    contents = [
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text = prompts.instruction1.format(user_details = user_details, prev_conv = "", curr_conv = text)),
                            ],),]
                    response = await asyncio.to_thread(gemini.models.generate_content,
                        model = TTT_MODEL,
                        contents = contents,
                        config = TTT_CONFIG,
                    )
                    t2 = time.time()
                    print(f"Time taken for TTT: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
                    response = json.loads(response.text)
                    print("TTT: ", response)
                    await self.text_out_queue.put(response['response'])
                        
        except websockets.exceptions.ConnectionClosedOK:
            print("STT WebSocket connection closed gracefully.")
            
        except Exception as e:
            print(f"Error receiving text from STT WebSocket: {e}")
                
    async def tts(self):
        try:
            while True:
                text = await self.text_out_queue.get()
                self.tts_connection.send_text(text)
                self.tts_connection.flush()
                print("Performing TTS...")
                '''if text != "Turn end":
                    self.tts_connection.send_text(text)
                else:
                    self.tts_connection.flush()'''
        except Exception as e:
            print(f"An error occurred in deepgram api: {e}")
                
    async def send_audio_to_client(self):
        while True:
            audio_data = await self.audio_out_queue.get()
            await self.client_ws.send(audio_data)
        
    async def main(self):
        self.audio_in_queue = asyncio.Queue(maxsize = 100)
        self.audio_out_queue = asyncio.Queue(maxsize = 100)
        self.text_in_queue = asyncio.Queue(maxsize = 50)
        self.text_out_queue = asyncio.Queue(maxsize = 50)
        
        try:
            self.stt_connection = deepgram.listen.asyncwebsocket.v("1")
            self.tts_connection = deepgram.speak.websocket.v("1")
            
            self.stt_connection.on(LiveTranscriptionEvents.Transcript, receive_stt_text)
            self.stt_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
            self.tts_connection.on(SpeakWebSocketEvents.AudioData, receive_tts_audio)
            
            stt_options = LiveOptions(
                model="nova-3",
                language="en-US",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                # To get UtteranceEnd, the following must be set:
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                # Time in milliseconds of silence to wait for before finalizing speech
                endpointing=300,)
            tts_options = SpeakWSOptions(
                model="aura-2-thalia-en",
                encoding="linear16",
                sample_rate=16000,
            )
            addons = {
                # Prevent waiting for additional numbers. when the speech is detected with numbers, additional numbers may come like ph number. So deepgram by default waits for some ms.
                "no_delay": "true"
            }
            if await self.stt_connection.start(stt_options, addons = addons) is False:
                print("Failed to start STT connection")
                return
            else:
                print("STT connection started successfully")
            if self.tts_connection.start(tts_options) is False:
                print("Failed to start TTS connection")
                return
            else:
                print("TTS connection started successfully")
            
            asyncio.create_task(self.stt())
            asyncio.create_task(self.ttt())
            asyncio.create_task(self.tts())
            asyncio.create_task(self.send_audio_to_client())
            
            async with websockets.serve(self.receive_client_audio, 'localhost', 8000):
                print("server running on ws://localhost:8000")
                await asyncio.Future()
                
        except websockets.exceptions.ConnectionClosedOK:
            print("WebSocket connection closed gracefully.")
 
 
if __name__ == "__main__": 
     server = Server()
     asyncio.run(server.main())   
        
