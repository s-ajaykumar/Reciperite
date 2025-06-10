import os
import json
import data.prompts as prompts
import requests
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket
from datetime import datetime
from dotenv import load_dotenv
from dataclasses import dataclass
from azure.cosmos import CosmosClient
import base64
import time
from google import genai
from google.genai import types

load_dotenv()


# Functions
class WS:
    def __init__(self):
        pass
    
    async def connect(self, websocket):
        await websocket.accept()
        self.websocket = websocket
        
    async def send_log(self, log):
        await self.websocket.send_text(json.dumps({"log" : log}))
        

class ServerRequest(BaseModel):
    user_id : str
    audio : str
    
class ServerResponse(BaseModel):
    response_text : str
    response_audio : str
    
@dataclass
class Config:
    DB_CONNECTION_STRING = os.environ["DB_CONNECTION_STRING"]
    #GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]


async def save_audio_out(out):
    file_name = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    with open(f"audio_outputs/{file_name}.wav", "wb") as f:
        f.write(out)
            
            
class AI:
    def __init__(self):
        self.client = genai.Client()
        
        self.ttt_model = "gemini-2.5-flash-preview-05-20"
        self.ttt_config = types.GenerateContentConfig(
            temperature=0,
            thinking_config = types.ThinkingConfig(
                thinking_budget=0,
            ),
            response_mime_type="application/json",
        )
        
    async def ttt(self, text):
        t1 = time.time()
        await ws.send_log(text)
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=text),
                ],
            ),
        ]
        
        response = self.client.models.generate_content(
            model=self.ttt_model,
            contents=contents,
            config=self.ttt_config,
        )
        
        await ws.send_log(json.loads(response.text))
        
        #Streaming response
        '''for chunk in self.client.models.generate_content_stream(
            model=self.ttt_model,
            contents=contents,
            config=self.ttt_config,
        ):
            print(chunk.text, end="")'''

        t2 = time.time()
        await ws.send_log(f"Time taken for TTT: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
        
        return json.loads(response.text)['response']   # Response json

    async def stt(self, audio):
        t1 = time.time()
        audio = base64.b64decode(audio)
        await ws.send_log(f"Converting speech to text")
        
        contents=[
            'Describe this audio clip',
            types.Part.from_bytes(
            data = audio_bytes,
            mime_type='audio/mp3',
            )
        ]
        audio = genai.upload_file(
            path="/Users/outbell/Ajay/DeepLearning/GenAI/Reciperite/audio_outputs/20250528T142147Z.wav"
        )

        response = self.ttt_model.generate_content(
                    contents = ["Transcript the audio",
                    audio]
                    )
        return response.text

    async def tts(self, text):
        t1 = time.time()
        
        out = self.tts_client.text_to_speech.generate(
            text=text,
            voice_id="en-US-natalie",
        )
        out = requests.get(out.audio_file)
        await save_audio_out(out.content)
        out = base64.b64encode(out.content).decode('utf-8')
        
        t2 = time.time()
        await ws.send_log(f"Time taken for TTS: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
        return out # Returns audio b64 data


class db:
    def __init__(self, connection_string):
        client = CosmosClient.from_connection_string(connection_string)
        self.database = client.get_database_client("Receipe")
        self.container = self.database.get_container_client("users")
        self.item_id = "user_details"
        
    async def get_user_details(self):
        await ws.send_log(f"{config.user_id}{self.item_id}")
        t1 = time.time()
        
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id)
        
        t2 = time.time()
        await ws.send_log(f"Fetched user_details - {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
        return item['details']  # Returns user details as a json
    
    async def get_prev_conversation(self):
        t1 = time.time()
        
        query = f"SELECT * FROM c WHERE c.user_id = '{config.user_id}' AND c.id != '{self.item_id}' ORDER BY c.id DESC OFFSET 0 LIMIT 1"
        items = list(self.container.query_items(
            query=query
        ))
        
        t2 = time.time()
        await ws.send_log(f"Fetched previous conversation - {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
        
        if not items:
            return None
        else:
            self.prev_conv_id = items[0]['id']  
            return ''.join(items[0]['conversations'])   # Returns a string of the previous conversation
        
    async def update_user_details(self, update_details):
        await ws.send_log(f"Updating user details")
        
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id)  
        for key, value in update_details.items():
            item['details'][key] = value
        self.container.replace_item(item=self.item_id, body = item)
        
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id) 
        await ws.send_log(f"Updated user details: \n{item['details']}")
        
    async def create_new_conversation(self, user_input, ai_response):
        await ws.send_log(f"Creating a new conversation")
        
        item = {
            "id": datetime.now().strftime('%Y%m%dT%H%M%SZ'),  # Unique ID based on current timestamp
            "user_id": config.user_id,
            "conversations": [user_input, ai_response]
        }
        self.container.create_item(body=item)
        
        await ws.send_log(f"New conversation created in db: \n{item}")
        
    async def update_conversation(self, user_input, ai_response, is_context_continued):
        await ws.send_log(f"Updating conversation")
        
        if is_context_continued != "True":
            await ws.send_log(f"Previous conversations is not related to current conversation.")
            await self.create_new_conversation(user_input, ai_response)
        else:
            await ws.send_log(f"Current conversation is related to previous conversation.")
            
            item = self.container.read_item(item = self.prev_conv_id, partition_key = config.user_id)
            item['conversations'].extend([user_input, ai_response])   # Extend new conversation
            self.container.replace_item(item = self.prev_conv_id, body=item)
            
            item = self.container.read_item(item = self.prev_conv_id, partition_key = config.user_id)
            await ws.send_log(f"Extended conversation in db : \n{item}")


# Initialize server, AI and database
app = FastAPI()
ws = WS()
config = Config()
call_ai = AI()
db_ops = db(config.DB_CONNECTION_STRING)   


@app.websocket('/ws')
async def websocket_endpoint(websocket : WebSocket):
    await ws.connect(websocket)
    while True:
        await websocket.receive_text()
     
        
@app.post('/call', response_model = ServerResponse)       
async def main(request : ServerRequest):
    config.user_id = request.user_id
    
    # Converting speech-to-text and getting previous timestep conversation asynchronously
    text = await call_ai.stt(request.audio)    
               
    prev_conversation = await db_ops.get_prev_conversation()
    user_details = await db_ops.get_user_details()
    
    if not prev_conversation:
        input = prompts.instruction.format(user_details = user_details, prev_conv = "No previous conversation", curr_conv = text)
        out = await call_ai.ttt(input)
        await db_ops.create_new_conversation('user: ' + text, "AI: " + out['response'])
    else:
        input = prompts.instruction.format(user_details = user_details, prev_conv = prev_conversation, curr_conv = text)
        out = await call_ai.ttt(input)
        await  db_ops.update_conversation('user: ' + text, "AI: " + out['response'], out['is_context_continued'])
    
    response_text = out["response"]  
    out = await call_ai.tts(out["response"])  
    return {"response_text" : response_text, "response_audio" : out}
    
    