import os
import json
import prompts
import openai
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket
from datetime import datetime
from dotenv import load_dotenv
from dataclasses import dataclass
from azure.cosmos import CosmosClient
from fastapi import WebSocket
import assemblyai as aai

load_dotenv()


# Prompts
tasks = [prompts.create_food_plan, prompts.create_recipe]

# Functions
class WS:
    def __init__(self):
        pass
    
    async def connect(self, websocket):
        self.websocket = websocket
        self.websocket.accept()
        
    async def send_log(self, log):
        await self.websocket.send_text(json.dumps({"log" : log}))
        

class ServerRequest(BaseModel):
    user_id : int
    audio : bytes
    
class ServerResponse(BaseModel):
    response_text : str
    response_audio : bytes
    
@dataclass
class Config:
    DB_CONNECTION_STRING = os.environ["DB_CONNECTION_STRING"]
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    
    
def new_or_continue_func(both_conv):
    out = call_ai.ttt(both_conv + "\n\n" + prompts.new_or_continue)
    if out["response"] == "new":
        config.is_continuing_conversation = False
    else:
        config.is_continuing_conversation = True


class AI:
    def __init__(self, openai_api_key):
        self.client = OpenAI(api_key = openai_api_key)

    def ttt(self, text):
        response = self.client.responses.create(
            model="gpt-4.1-nano",
            input = text
            )
        return response.output_text   # Response json

    async def stt(audio):
        await ws.send_log(f"Converting speech to text")
        
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
        transcript = aai.Transcriber(config=config).transcribe(audio)

        if transcript.status == "error":
            raise RuntimeError(f"Transcription failed: {transcript.error}")

        await ws.send_log(f"Converted speech to text : {transcript["text"]}")
        return transcript.text   # Response string

    def tts(text):
        response = openai.Audio.speech.create(
            model="tts-1",
            voice="nova",  # Other options: alloy, echo, fable, onyx, shimmer
            input = text
            )
        file_name = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        with open(f"{file_name}.mp3", "wb") as f:
            f.write(response.content)
        return f"{file_name}.mp3"       # Returns mp3 bs64 encoded string


class db:
    def __init__(self, connection_string):
        client = CosmosClient.from_connection_string(connection_string)
        self.database = client.get_database_client("Receipe")
        self.container = self.database.get_container_client("users")
        self.item_id = "user_details"
        
    async def get_user_details(self):
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id)
        
        await ws.send_log(f"Fetched user_details")
        return item['details']  # Returns user details as a json
    
    async def get_prev_conversation(self):
        query = f"SELECT * FROM c WHERE c.user_id = '{config.user_id}' AND c.id != '{self.item_id}' ORDER BY c.id DESC OFFSET 0 LIMIT 1"
        items = list(self.container.query_items(
            query=query
        ))
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
            self.create_new_conversation(user_input, ai_response)
        else:
            await ws.send_log(f"Current conversation is related to previous conversation.")
            
            item = self.container.read_item(item = config.prev_conv_id, partition_key = config.user_id)
            item['conversations'].extend([user_input, ai_response])   # Extend new conversation
            self.container.replace_item(item = config.prev_conv_id, body=item)
            
            item = self.container.read_item(item = config.prev_conv_id, partition_key = config.user_id)
            await ws.send_log(f"Extended conversation : \n{item}")


class task_router:
    def __init__(self, tasks, route_task_prompt):
        self.tasks = tasks
        self.route_task_prompt = route_task_prompt
        
    async def __call__(self, text, user_details):
        out = call_ai.ttt(inputs = text + "\n\n" + self.route_task_prompt)
        idx = int(out["response"])
        input = "user_details :\n" + user_details + "\n\nConversations:\n" + text + "\n\n" + self.tasks[idx]
        
        if idx == 2:
            return call_ai.tts("Sorry! I can't help with that.")
        elif idx == 0:
            await ws.send_log(f"Routing to food planner")
            
            out = await self.food_planner(input)
            return out
        elif idx == 1:
            await ws.send_log(f"Routing to recipe creator")
            
            out = await self.recipe_creator(input)
            return out

    async def food_planner(self, input):
        await ws.send_log(f"User : {input}")
        
        out = call_ai.ttt(input)
        
        await ws.send_log(f"AI : {out}")
        
        if out["update_details"] != "None":
            await db_ops.update_user_details(out["update_details"])
        return out 
    
    async def recipe_creator(self, input):
        await ws.send_log(f"User : {input}")
        
        out = call_ai.ttt(input)
        
        await ws.send_log(f"AI : {out}")
        return out


# Initialize server, AI and database
app = FastAPI()
ws = WS()
config = Config()
call_ai = AI(config.OPENAI_API_KEY)
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
    await ws.send_log(f"user(stt): {text}")     
               
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
        new_or_continue_func(both_conv)
        
        if not config.is_continuing_conversation:
            await ws.send_log(f"Not continuing conversation")
            
            out = await route_task(text, user_details)
        else:
            await ws.send_log(f"Continuing conversation")
            
            out = await route_task(prev_conversation + "\n" + text, user_details)
            
        await  db_ops.update_conversation(text, "AI: " + out['response'])
        
    out = call_ai.tts(out["response"])    # Returns mp3 file path
    return {"response" : out}
    
    