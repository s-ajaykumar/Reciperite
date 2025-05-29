import os
import json
import prompts
import requests
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket
from datetime import datetime
from dotenv import load_dotenv
from dataclasses import dataclass
from azure.cosmos import CosmosClient
from fastapi import WebSocket
import assemblyai as aai
from murf import Murf
import base64
import time
import google.generativeai as genai

load_dotenv()


# Prompts
tasks = [prompts.create_food_plan, prompts.create_recipe]

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
    GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
    ASSEMBLY_AI_API_KEY = os.environ["ASSEMBLY_AI_API_KEY"]
    MURF_API_KEY = os.environ["MURF_API_KEY"]
    
    
async def new_or_continue_func(both_conv):
    t1 = time.time()
    out = await call_ai.ttt(both_conv + "\n\n" + prompts.new_or_continue)
    t2 = time.time()
    ws.send_log(f"Time taken for checking the conversation new_or_continue: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
    
    if out["response"] == "new":
        config.is_continuing_conversation = False
    else:
        config.is_continuing_conversation = True


async def save_audio_out(out):
    file_name = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    with open(f"audio_outputs/{file_name}.wav", "wb") as f:
        f.write(out)
            
            
class AI:
    def __init__(self, ttt_key, stt_key, tts_key):
        genai.configure(api_key=ttt_key)
        self.ttt_model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        
        aai.settings.api_key =  stt_key
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
        self.transcriber = aai.Transcriber(config=config)
        
        self.tts_client = Murf(
            api_key=tts_key,
        )
        
    async def ttt(self, text):
        t1 = time.time()
        
        await ws.send_log(text)
        # Generate content
        response = self.ttt_model.generate_content(
            text,
            generation_config={
                "temperature" : 0,
                "response_mime_type": "application/json"
            })
        print(response.text)
        
        t2 = time.time()
        await ws.send_log(f"Time taken for TTT: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
        
        return json.loads(response.text)   # Response json

    async def stt(self, audio):
        t1 = time.time()
        audio = base64.b64decode(audio)
        await ws.send_log(f"Converting speech to text")

        transcript = self.transcriber.transcribe(audio)

        if transcript.status == "error":
            raise RuntimeError(f"Transcription failed: {transcript.error}")

        t2 = time.time()
        await ws.send_log(f"Time taken for STT: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
        await ws.send_log(f"Converted speech to text : {transcript.text}")
        
        return transcript.text   # Response string

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
        
        await ws.send_log(f"New conversation : \n{item}")
        
    async def update_conversation(self, user_input, ai_response):
        await ws.send_log(f"Updating conversation")
        
        if not config.is_continuing_conversation:
            await ws.send_log(f"Previous conversations is not related to current conversation.")
            await self.create_new_conversation(user_input, ai_response)
        else:
            await ws.send_log(f"Current conversation is related to previous conversation.")
            
            item = self.container.read_item(item = self.prev_conv_id, partition_key = config.user_id)
            item['conversations'].extend([user_input, ai_response])   # Extend new conversation
            self.container.replace_item(item = self.prev_conv_id, body=item)
            
            item = self.container.read_item(item = self.prev_conv_id, partition_key = config.user_id)
            await ws.send_log(f"Extended conversation : \n{item}")


class task_router:
    def __init__(self, tasks, route_task_prompt):
        self.tasks = tasks
        self.route_task_prompt = route_task_prompt
        
    async def __call__(self, text, user_details):
        t1 = time.time()
        
        out = await call_ai.ttt(text + "\n\n" + self.route_task_prompt)
        idx = int(out["response"])
        input = "user_details :\n" + str(user_details) + "\n\nConversations:\n" + text + "\n\n" + self.tasks[idx]
        
        if idx == 2:
            return call_ai.tts("Sorry! I can't help with that.")
        elif idx == 0:
            await ws.send_log(f"Routing to food planner")
            
            out = await self.food_planner(input)
            return out
        elif idx == 1:
            await ws.send_log(f"Routing to recipe creator")
            
            out = await self.recipe_creator(input)
            if out:
                t2 = time.time()
                await ws.send_log(f"Time taken for task routing: {t2-t1:3f}sec {(t2 - t1)*1000:4f} ms")
            return out

    async def food_planner(self, input):
        await ws.send_log(f"User : {input}")
        
        out = await call_ai.ttt(input)
        
        await ws.send_log(f"AI : {out}")
        
        if out["update_details"] != "None":
            await db_ops.update_user_details(out["update_details"])
        return out 
    
    async def recipe_creator(self, input):
        await ws.send_log(f"User : {input}")
        
        out = await call_ai.ttt(input)
        
        await ws.send_log(f"AI : {out}")
        return out


# Initialize server, AI and database
app = FastAPI()
ws = WS()
config = Config()
call_ai = AI(config.GOOGLE_API_KEY, config.ASSEMBLY_AI_API_KEY, config.MURF_API_KEY)
db_ops = db(config.DB_CONNECTION_STRING)   
route_task = task_router(tasks, prompts.route_task_prompt)


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
    text = "user : " + text
    
    if not prev_conversation:
        await ws.send_log(f"No previous conversation")
        
        out = await route_task(text, user_details)
        await db_ops.create_new_conversation(text, "AI: " + out['response'])
    else:
        await ws.send_log(f"Fetched prev conversation")
        
        both_conv = "previous conversation :\n" + prev_conversation + "\n" + "current conversation:\n" +  text
        
        await ws.send_log(f"Checking if current conversation is related to previous conversation")
        await new_or_continue_func(both_conv)
        
        if not config.is_continuing_conversation:
            await ws.send_log(f"Not continuing conversation")
            
            out = await route_task(text, user_details)
        else:
            await ws.send_log(f"Continuing conversation")
            
            out = await route_task(prev_conversation + "\n" + text, user_details)
            
        await  db_ops.update_conversation(text, "AI: " + out['response'])
    
    response_text = out["response"]  
    out = await call_ai.tts(out["response"])  
    return {"response_text" : response_text, "response_audio" : out}
    
    