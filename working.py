import os
from fastapi import FastAPI
from datetime import datetime
from dotenv import load_dotenv
from dataclasses import dataclass
from azure.cosmos import CosmosClient, PartitionKey

load_dotenv()


# Prompts
new_or_continue = """
response_template = {
    "response": ""
}
# Task: Determine if the user is new or continuing the conversation
1. Compare the current conversation with the previous conversation and if the user initiates a new conversation, then assign "new" to response_template["response"] or if the user continues the previous conversation, then assign "continue" to response_template["response"]. Don't assign anything other than these.
2. Perform the task and return the json file.
\n 
"""
route_task_prompt = """
response_template = {
    "response": ""
}

tasks = [create a food plan, create a recipe, others]

# Task
1. The conversation is related to any one of the above tasks. So identify the task's index related to the conversation and assign the task's index to the response_template["response"]. Don't assign anything to it other than the mentioned. Note that index starts from 0.
2. Perform the task and return the json file.
"""
create_food_plan = """response_template = {
response : "",
update_details : "None"
}

details = [
    "Weekly plan or a single daily plan",
    "Daily activity level (e.g., less active, moderately active, very active)",
    "Typical meal schedule (number of meals per day)",
    "Target weight or weight loss goal for example lose 5 kg in 2 months)"
  ]

tasks = {
"task_1" : "See through the <user_details> and <previous_conversations> and figure out whether the <user_details> contains the "details" to create a food plan. If "yes", then create a recipe plan with the "details" you have and provide the response as a value to the "response" key in the response template. The response must contain only the recipe plan, no other words should be present in it and don't use "\n" in your response instead use "   ". If "no", then ask the "details" to the user as a value to the "final_response" key in the response template. If asking the "details" to the user then follow the following steps: "Only questions should be present in your response. No other words should be present.", "Ask one question at a time.", "If options are available for your question then give options for your question like "what is you daily activity level? Is it less active or very active or moderately active".",
"task_2" : "See through the user_details and check if any of them is "None". If "no" then don't do anything and ignore the following steps. If "yes", then see through the conversation whether the user provided the details for the user_details which has "None". If "yes", then create a azure cosmos_db for no_sql command to update details for the user id and assign the command as a value to the "update_details" key in the "response_template". If "no", then don't don't do anything."
}
Perform the tasks and return the json file."""
create_recipe = """
response_template = {
    "response": ""
}

# Task
1. Do what the user asked, assign the response to the response_template["response"] and return the json file.
"""

prompts = [create_food_plan, create_recipe]

# Functions
@dataclass
class Config:
    DB_CONNECTION_STRING = os.environ["DB_CONNECTION_STRING"]
    
    
def new_or_continue_func(both_conv):
    out = call_ai(prompt = new_or_continue, inputs = both_conv)
    if out["response"] == "new":
        config.is_continuing_conversation = False
    else:
        config.is_continuing_conversation = True


class AI:
    def __init__(self, ttt_endpoint, ttt_key, stt_endpoint, stt_key, tts_endpoint, tts_key):
        self.ttt_client = "" # text-to-text AI client
        self.stt_client = "" # speech-to-text AI client
        self.tts_client = "" # text-to-speech AI client

    def ttt(self, text):
        out = ""
        return out
    
    async def stt(mp3_file):
        return await call_ai(mp3_file)

    def tts(text):
        return "" # Call tts(text)
    

class db:
    def __init__(self, connection_string):
        client = CosmosClient.from_connection_string(connection_string)
        self.database = client.get_database_client("Receipe")
        self.container = self.database.get_container_client("users")
        self.item_id = "user_details"
        
    async def get_user_details(self):
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id)
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
        item = self.container.read_item(item = self.item_id, partition_key = config.user_id)  # Ensure the item exists
        for key, value in update_details.items():
            item['details'][key] = value
        self.container.replace_item(item=self.item_id, body = item)
        
    async def create_new_conversation(self, user_input, ai_response):
        item = {
            "id": datetime.now().strftime('%Y%m%dT%H%M%SZ'),  # Unique ID based on current timestamp
            "user_id": config.user_id,
            "conversations": [user_input, ai_response]
        }
        self.container.create_item(body=item)
        
    async def update_conversation(self, user_input, ai_response):
        if not config.is_continuing_conversation:
            self.create_new_conversation(user_input, ai_response)
        else:
            item = self.container.read_item(item = config.prev_conv_id, partition_key = config.user_id)
            item['conversations'].extend([user_input, ai_response])  # Append new conversation
            self.container.replace_item(item = config.prev_conv_id, body=item)


class task_router:
    def __init__(self, prompts, route_task_prompt):
        self.prompts = prompts
        self.route_task_prompt = route_task_prompt
        
    async def __call__(self, text, user_details):
        self.text = text
        out = call_ai(prompt = self.route_task_prompt, inputs = self.text)
        idx = int(out["response"])
        input = "user_details :\n" + user_details + "\n\n" + self.text
        
        if idx == 2:
            return call_ai.tts("Sorry! I can't help with that.")
        elif idx == 0:
            out = await self.food_planner(self.prompts[idx], input)
            return out
        elif idx == 1:
            out = self.recipe_creator(self.prompts[idx], input)
            return out

    async def food_planner(self, prompt, input):
        out = call_ai.ttt(prompt = prompt, inputs = input)
        if out["update_details"] != "None":
            await db_ops.update_user_details(out["update_details"])
        return out 
    
    def recipe_creator(self, prompt, input):
        out = call_ai(prompt = prompt, inputs = input)
        return out


# Initialize server, AI and database
app = FastAPI()
config = Config()
call_ai = AI(config.ttt_endpoint, config.ttt_key, config.stt_endpoint, config.stt_key, config.tts_endpoint, config.tts_key)
db_ops = db(config.DB_CONNECTION_STRING)   
route_task = task_router(prompts, route_task_prompt)


@app.post('/call/{user_id}/{input}')        # input : mp3 format
async def call(user_id : int, mp3_file):
    config.user_id = user_id
    
    # Converting speech-to-text and getting previous timestep conversation asynchronously
    text = await call_ai.stt(mp3_file)                 
    prev_conversation = await db_ops.get_prev_conversation()
    user_details = await db_ops.get_user_details()
    text = "user : " + text
    
    if not prev_conversation:
        out = await route_task(text, user_details)
        await db_ops.create_new_conversation(text, "AI: " + out['response'])
    else:
        both_conv = "previous conversation :\n" + prev_conversation + "\n" + "current conversation:\n" +  text
        new_or_continue_func(both_conv)
        if not config.is_continuing_conversation:
            out = await route_task(text, user_details)
        else:
            out = await route_task(both_conv, user_details)
        await  db_ops.update_conversation(text, "AI: " + out['response'])
        
    out = call_ai.tts(out["response"])    # Returns mp3
    return out
    
    