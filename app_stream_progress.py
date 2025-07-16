'''
This code is different from the app.py in the following ways:
1. STT used =     Deepgram,       TTT used =          Gemini 2.5 flash,             TTS used -         Cartesia 
2. Websockets are used here to receive streaming audio data and to stream the TTS audio data to the client.
3. TTS with timestamps are implemented here instead of just TTS.
4. Implemented database for context retrieval
5. Implemented highlighting line by line (or) specific part.
'''





import data.prompts as prompts
import data.config as config


from dotenv import load_dotenv
import time
import json
import os
from datetime import datetime

import websockets
import ngrok
import asyncio
import base64

from azure.cosmos import CosmosClient

from google import genai
from google.genai import types
from cartesia import AsyncCartesia
from deepgram import (LiveTranscriptionEvents, DeepgramClient)

load_dotenv()





class DB:
    def __init__(self):
        client = CosmosClient.from_connection_string(os.environ["DB_CONNECTION_STRING"])
        database = client.get_database_client("Receipe")
        self.container = database.get_container_client("users")
        self.item_id = "user_details"
        
    
    async def get_user_details(self, user_id):
        t1 = time.time()
        print(user_id)
        try:
            item = self.container.read_item(item = self.item_id, partition_key = user_id)
            
        except Exception as e:
            print("error in getting details ", e)
        t2 = time.time()
        print("DB time taken for retrieving user details:", (t2 - t1)*1000, "  ms")
        return item['details']  
    
    async def get_prev_conversation(self, user_id):
        t1 = time.time()
        query = f"SELECT * FROM c WHERE c.user_id = '{user_id}' AND c.id != '{self.item_id}' ORDER BY c.id DESC OFFSET 0 LIMIT 1"
        items = list(self.container.query_items(
            query = query
        ))
        t2 = time.time()
        print(f"Time taken for fetching previus conversation- {(t2 - t1)*1000:4f} ms")
        
        if not items:
            return "", ""
        else:
            prev_conv_id = items[0]['id']  
            return prev_conv_id, ''.join(items[0]['conversations'])   # Returns a string of the previous conversation
        
    async def update_user_details(self, update_details):
        await ws.send_log(f"Updating user details")
        
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id)  
        for key, value in update_details.items():
            item['details'][key] = value
        self.container.replace_item(item=self.item_id, body = item)
        
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id) 
        await ws.send_log(f"Updated user details: \n{item['details']}")
        
    async def create_new_conversation(self, user_id, user_input, ai_response):
        t1 = time.time()
        print(f"Creating a new conversation")
        
        item = {
            "id": datetime.now().strftime('%Y%m%dT%H%M%SZ'),  # Unique ID based on current timestamp
            "user_id": user_id,
            "conversations": [user_input, ai_response]
        }
        self.container.create_item(body = item)
        
        t2 = time.time()
        print(f"Time taken for uploading latest conversation to DB: ", (t2-t1)*1000, " ms\n\n")
        return item["id"]
        
    async def update_conversation(self, prev_conv_id, user_id, user_input, ai_response, is_context_continued):
        if is_context_continued != "True" or prev_conv_id == "":
            print(f"Previous conversations is not related to current conversation.\n\n")
            conv_id = await self.create_new_conversation(user_id, user_input, ai_response)
            return 'new', conv_id
            
        else:
            t1 = time.time()
            print(f"Current conversation is related to previous conversation.\n\n")
            item = self.container.read_item(item = prev_conv_id, partition_key = user_id)
            item['conversations'].extend([user_input, ai_response])  
            self.container.replace_item(item = prev_conv_id, body = item)
            t2 = time.time()
            print("Time taken for Updating conversation in DB: ", (t2-t1)*1000, " ms\n\n")
            return 'continue', ""

    
    
    
class ClientHandler:
    def __init__(self, client_id, ws):
        self.client_id = client_id
        self.client_ws = ws
        
        self.stt_connection = None
        self.tts_connection = None
        self.gemini = None
        
        self.prev_conv = None
        self.prev_conv_id = None
        self.user_details = None
        
        self.audio_in_queue = asyncio.Queue(maxsize = 100)
        self.audio_out_queue = asyncio.Queue(maxsize = 100)
        self.text_in_queue = asyncio.Queue(maxsize = 50)
        self.text_out_queue = asyncio.Queue(maxsize = 50)
        self.is_finals = []
     
     
    async def save_conversation_in_db(self, text, response):
        print(response)
        if response['task'] != "unrelated":
            conv, conv_id = await db.update_conversation(prev_conv_id = self.prev_conv_id,
                                                        user_id = self.client_id, 
                                                        user_input = "User: " + text + "\n", 
                                                        ai_response = "AI: " + str(response['data']) + "\n\n", 
                                                        is_context_continued = response['is_context_continued'])
            curr_conv = "User: "+text+"\n"+"AI: "+str(response['data'])+"\n\n"
            
            if conv == 'new':
                self.prev_conv_id = conv_id
                self.prev_conv = curr_conv
            else:
                self.prev_conv += curr_conv
        
    async def format_TTT_response(self, response):
        if response['task'] == "create_food_plan":
                    if type(response['data']) is not str:
                        response = response['data']['question']
                        
        elif response['task'] == "create_recipe":
            await self.client_ws.send(json.dumps(response))
            tts_input = response['data']['question']
            return tts_input
                     
        elif response['task'] == "guiding_in_ingredients":
            await self.client_ws.send(json.dumps({"task" : response['task'], "index" : response['data']['index']}))
            tts_input = response['data']['ingredients']
            return tts_input
        
        elif response['task'] == "guiding_in_instructions":
            await self.client_ws.send(json.dumps({"task" : response['task'], "index" : response['data']['index']}))
            tts_input = response['data']['instruction']
            return tts_input
        
        elif response['task'] == "unrelated":
            tts_input = response['data']
            return tts_input
        
    async def format_contents(self, text):
        contents = [
            types.Content(
                role = "user",
                parts = [
                    types.Part.from_text(text = "Previous conversations:\n"+self.prev_conv+"\n\n"+"Current query:\n"+text)
                ],
            )
        ]
        return contents
    
    async def get_ttt_config(self):
        config = types.GenerateContentConfig(
            temperature = 1,
            system_instruction = [types.Part.from_text(text = prompts.instruction.format(user_details = str(self.user_details)))],
            thinking_config = types.ThinkingConfig(
                thinking_budget = 0,
            ),
            response_mime_type = "application/json",
        )
        return config
    
    async def on_new_speech(self):
        await self.client_ws.send(json.dumps({'type' : 'control_msg', 'data' : 'stop'}))
                
        while not self.text_in_queue.empty():
            await self.text_in_queue.get_nowait()
        while not self.text_out_queue.empty():
            await self.text_out_queue.get_nowait()
        while not self.audio_out_queue.empty():
            await self.audio_out_queue.get_nowait()
            
        print("\tyes cleared")
                    
    async def on_tts_response(self, tts_response):
        async for out in tts_response:
            audio_data = base64.b64encode(out.audio).decode('utf-8')
            audio_data = {"task" : "audio", "data" : audio_data}
            self.audio_out_queue.put_nowait(audio_data)
        
    async def on_stt_response(self, deepgram_self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        
        if len(sentence) == 0:
            return
        
        if result.is_final:
            self.is_finals.append(sentence)
            
            if result.speech_final:
                utterance = " ".join(self.is_finals)
                
                print(f"\t\tClient {self.client_id}")
                print("New Speech started")
                
                await self.on_new_speech()
                print("Clearing existing queues...\n\n", end = '')
                
                await self.text_in_queue.put(utterance)
                print(f"STT: {utterance}\n")
                self.is_finals = []


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
               
                contents = await self.format_contents(text)
                ttt_config = await self.get_ttt_config()
                
                t1 = time.time()
                response = await asyncio.to_thread(self.gemini.models.generate_content,
                    model = config.TTT.MODEL,
                    contents = contents,
                    config = ttt_config,
                )
                t2 = time.time()
                response = json.loads(response.text)
                print(f"\t\t\t\tClient: {self.client_id}\nUser: {text}\nAI:\nTask:\t{response['task']}\n{response['data']}\n\nTIME TAKEN: {t2-t1:3f}s {(t2 - t1)*1000:4f} ms\n\n")
                
                tts_input = await self.format_TTT_response(response)   
                await self.text_out_queue.put(tts_input)
                await self.save_conversation_in_db(text, response)
                
                        
        except websockets.exceptions.ConnectionClosedOK:
            print("TTT WebSocket connection closed gracefully.")
            
        except Exception as e:
            print(f"TTT Error receiving text from TTT WebSocket: {e}")
                
    async def tts(self):
        try:
            while True:
                tts_input = await self.text_out_queue.get()
                    
                voice = config.TTS.voice.copy()
                voice["__experimental_controls"] = {
                                "speed": "slowest"              # or "slowest", or a float like -0.5
                            }
                tts_response = await self.tts_connection.send(
                                model_id = config.TTS.model_id,
                                transcript = tts_input,
                                voice = voice,
                                output_format = config.TTS.output_format,
                                add_timestamps = False,    
                                stream = config.TTS.stream
                            )
                await self.on_tts_response(tts_response)
                    
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
            deepgram: DeepgramClient = DeepgramClient("", config.STT.CONFIG)
            self.stt_connection = deepgram.listen.asyncwebsocket.v("1")
            self.stt_connection.on(LiveTranscriptionEvents.Transcript, lambda deepgram_self, result, **kwargs: self.on_stt_response(deepgram_self, result, **kwargs))
            await self.stt_connection.start(config.STT.OPTIONS, addons = config.STT.ADDONS)
            print("STT connected for client: ", self.client_id)
        
        except Exception as e:
            print("Failed to connect to STT websocket for client: ", self.client_id)  
            return False  
                
                
        try:
            self.gemini = genai.Client()
            print("TTT connected for client: ", self.client_id)
            
        except Exception as e:
            print("Failed to  connect to TTT client for client: ", self.client_id)
            return False
            
            
        try:  
            self.tts_client = AsyncCartesia(api_key = os.getenv("CARTESIA_API_KEY"))
            self.tts_connection = await self.tts_client.tts.websocket()
            print(f"TTS connectied for client: {self.client_id}")
            
        except Exception as e:
            print(f"Failed to connect to TTS WebSocket for client {self.client_id}: {e}")
            return False
        
        
        try:
            self.user_details = await db.get_user_details(self.client_id)
            self.prev_conv_id, self.prev_conv = await db.get_prev_conversation(self.client_id)
            
            if not self.prev_conv:  
                print("New User\n\n")
                
            
        except Exception as e:
            print("Error in retrieving user details/previous conversation from the db")
            return False
        
        return True
    
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
                asyncio.create_task(self.send_audio_to_client())
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
                
            print(f"Client {self.client_id} handler finished")
 
 
 
 
class Server:
    def __init__(self):
        self.clients = {}
        self.tunnel = None
     
    async def handle_new_client(self, ws):
        client_id = "001"                           #str(uuid.uuid4())
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
        public_ws_url = await self.start_tunnel()
        
        try:
            async with websockets.serve(self.handle_new_client, '0.0.0.0', 8080):
                print("Server running on ws://0.0.0.0:8080")
                
                if public_ws_url:
                        print(f"Clients can connect to: {public_ws_url}")
                else:
                    print("Local access only: ws://localhost:8000")
                        
                await asyncio.Future()
        
        except KeyboardInterrupt:
            print("Server shutting down...")
            
        finally:
            await self.stop_tunnel()
         
    
    
    

if __name__ == "__main__": 
     db = DB()
     print("Connected to database\n")
     server = Server()
     asyncio.run(server.main())   
        

        
