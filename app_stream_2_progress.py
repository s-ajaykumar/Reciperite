import data.prompts as prompts

from dotenv import load_dotenv
import time
import json
import uuid
import os

import websockets
import ngrok
import asyncio

from google import genai
from google.genai import types

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

DEEPGRAM_CONFIG: DeepgramClientOptions = DeepgramClientOptions(options={"keepalive": "true"})
deepgram: DeepgramClient = DeepgramClient("", DEEPGRAM_CONFIG)


  
    
class ClientHandler:
    def __init__(self, client_id, ws):
        self.client_id = client_id
        self.client_ws = ws
        self.stt_connection = None
        self.tts_connection = None
        
        self.audio_in_queue = asyncio.Queue(maxsize = 100)
        self.audio_out_queue = asyncio.Queue(maxsize = 100)
        self.text_in_queue = asyncio.Queue(maxsize = 50)
        self.text_out_queue = asyncio.Queue(maxsize = 50)
        self.is_finals = []
        
    async def receive_stt_text(self, deepgram_self, result, **kwargs):
        if result["type"] == "SpeechStarted":
            print(f"Client {self.client_id} New Speech Started\n\n")
            self.client_ws.send("New speech started")
            
        sentence = result.channel.alternatives[0].transcript
        print(sentence)
        
        if len(sentence) == 0:
            return
        
        if result.is_final:
            self.is_finals.append(sentence)
            
            if result.speech_final:
                utterance = " ".join(self.is_finals)
                await self.text_in_queue.put(utterance)
                print(f"Client {self.client_id}\nSTT:\n{utterance}\n\n")
                self.is_finals = []
            
    async def on_utterance_end(self, deepgram_self, utterance_end, **kwargs):
        if len(self.is_finals) > 0:
            utterance = " ".join(self.is_finals)
            await self.text_in_queue.put(utterance)
            print(f"Client: {self.client_id}\nSTT:\n{utterance}\n\n")
            self.is_finals = []
                    
    async def receive_tts_audio(self, deepgram_self, data, **kwargs):
        self.audio_out_queue.put_nowait(data)
     
     
     
     
    async def receive_client_audio(self):
        try:
            async for chunk in self.client_ws:
                await self.audio_in_queue.put(chunk)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {self.client_id} disconnected")
        except Exception as e:
            print(f"Error receiving audio from client {self.client_id}: {e}")
            
    async def stt(self):
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                if self.stt_connection:
                    await self.stt_connection.send(chunk)
                    
        except Exception as e:
            print(f"STT ERROR for client {self.client_id}: occurred while sending audio: {e}")
              
    async def ttt(self):
        try:
            while True:
                text = await self.text_in_queue.get()
                if text:           
                    t1 = time.time()
                    contents = [
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text = prompts.instruction.format(user_details = user_details, prev_conv = "", curr_conv = text)),
                            ],),]
                    response = await asyncio.to_thread(gemini.models.generate_content,
                        model = TTT_MODEL,
                        contents = contents,
                        config = TTT_CONFIG,
                    )
                    t2 = time.time()
                    response = json.loads(response.text)
                    
                    if response['task'] == "create a food plan":
                        if type(response['response']) is not str:
                            response = response['response']['question']
                            
                    response = response['response']
                    await self.text_out_queue.put(response)
                    print(f"Client: {self.client_id}\nTTT:\n{response}\nTIME TAKEN: {t2-t1:3f}s {(t2 - t1)*1000:4f} ms\n\n")
                    
                        
        except websockets.exceptions.ConnectionClosedOK:
            print("TTT WebSocket connection closed gracefully.")
            
        except Exception as e:
            print(f"TTT Error receiving text from TTT WebSocket: {e}")
                
    async def tts(self):
        try:
            while True:
                text = await self.text_out_queue.get()
                if self.tts_connection:
                    await self.tts_connection.send_text(text)
                    await self.tts_connection.flush()
                    print("Sent text to TTS connection\n\n\n\n")
                    
        except Exception as e:
            print(f"TTS ERROR: {e}")
                
    async def send_audio_to_client(self):
        try:
            while True:
                audio_data = await self.audio_out_queue.get()
                await self.client_ws.send(audio_data)
        
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {self.client_id} connection closed while sending audio")
        
        except Exception as e:
            print(f"Error sending audio to client {self.client_id}: {e}")
            
        
        
        
    async def setup_connections(self):
        try:
            self.stt_connection = deepgram.listen.asyncwebsocket.v("1")
            self.tts_connection = deepgram.speak.asyncwebsocket.v("1")
            
            self.stt_connection.on(LiveTranscriptionEvents.Transcript, lambda deepgram_self, result, **kwargs: self.receive_stt_text(deepgram_self, result, **kwargs))
            self.stt_connection.on(LiveTranscriptionEvents.UtteranceEnd, lambda deepgram_self, utterance_end, **kwargs: self.on_utterance_end(deepgram_self, utterance_end, **kwargs))
            self.tts_connection.on(SpeakWebSocketEvents.AudioData, lambda deepgram_self, data, **kwargs: self.receive_tts_audio(deepgram_self, data, **kwargs))
            
            stt_options = LiveOptions(model="nova-3", language="en-US", smart_format=True, encoding="linear16", channels=1, 
                                    sample_rate=16000, vad_events=True, interim_results = True, utterance_end_ms = 1000, endpointing=300)
            
            tts_options = SpeakWSOptions(model="aura-2-arcas-en", encoding="linear16", sample_rate=16000,)
            
            addons = {"no_delay": "true"}
            
            if await self.stt_connection.start(stt_options, addons = addons) is False:
                print(f"Failed to start STT connection for client {self.client_id}")
                return False
            else:
                print(f"STT connection started successfully for client {self.client_id}")
                
            if await self.tts_connection.start(tts_options) is False:
                print(f"Failed to start TTS connection for client {self.client_id}")
                return False
            else:
                print(f"TTS connection started successfully for client {self.client_id}")
            
            return True
            
        except Exception as e:
            print(f"ERROR: setting up connections for client {self.client_id}: {e}")
            return False
        
    async def handle_client(self):
        try:
            if not await self.setup_connections():
                print(f"Failed to setup connections for client {self.client_id}")
                await self.client_ws.close()
                return
            
            
            tasks = [
                asyncio.create_task(self.receive_client_audio()),
                asyncio.create_task(self.stt()),
                asyncio.create_task(self.ttt()),
                asyncio.create_task(self.tts()),
                asyncio.create_task(self.send_audio_to_client()),
                ]
            
            done, pending = await asyncio.wait(tasks, return_when = asyncio.FIRST_COMPLETED)
            
            for task in pending:
                task.cancel()
                
        except Exception as e:
            print(f"ERROR: handling client {self.client_id}: {e}")
            
        finally:
            if self.stt_connection:
                try:
                    await self.stt_connection.finish()
                except:
                    pass 
            if self.tts_connection:
                try:
                    await self.tts_connection.finish()
                except:
                    pass
            print(f"Client {self.client_id} handler finished")
 
 
 
 
class Server:
    def __init__(self):
        self.clients = {}
        self.tunnel = None
     
    async def handle_new_client(self, ws):
        client_id = str(uuid.uuid4())
        print(f"New client connected: {client_id}")
        try:
            await ws.accept() if hasattr(ws, 'accept') else None
            client_handler = ClientHandler(client_id, ws)
            self.clients[client_id] = client_handler
            
            await client_handler.handle_client()
            
        except Exception as e:
            print(f"ERROR: with client {client_id} : {e}")
            
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
                print(f"Client {client_id} removed from active clients")
     
    async def start_tunnel(self):
        try:
            ngrok.set_auth_token(os.environ['NGROK_AUTH_TOKEN'])
            self.tunnel = await ngrok.connect(8080, "http", domain = "promoted-solid-gannet.ngrok-free.app")
            public_url = self.tunnel.url()
            ws_url = public_url.replace("http://", "ws://").replace("https://", "wss://")
            print(f"🌍 Server accessible publicly at: {ws_url}")
            print(f"🔗 Ngrok tunnel: {public_url}")
            return ws_url
        
        except Exception as e:
            print(f"Failed to start ngrok tunnel: {e}")
            return None
    
    async def stop_tunnel(self):
        if self.tunnel:
            await ngrok.disconnect(self.tunnel.public_url)
            print("Ngrok tunnel stopped")
           
    async def main(self):
        #public_ws_url = await self.start_tunnel()
        
        try:
            async with websockets.serve(self.handle_new_client, '0.0.0.0', 8080):
                print("Server running on ws://0.0.0.0:8080")
                
                '''if public_ws_url:
                        print(f"Clients can connect to: {public_ws_url}")
                else:
                    print("Local access only: ws://localhost:8000")'''
                        
                await asyncio.Future()
        
        except KeyboardInterrupt:
            print("Server shutting down...")
            
        finally:
            await self.stop_tunnel()
         
    
if __name__ == "__main__": 
     server = Server()
     asyncio.run(server.main())   
        
