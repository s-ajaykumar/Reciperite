import os
import time
import asyncio
from fastapi import FastAPI
from dotenv import load_dotenv
from dataclasses import dataclass
from azure.core.exceptions import AzureError
from azure.cosmos import CosmosClient, PartitionKey

load_dotenv()


# Prompts
new_or_continue = """
response_template = {
    "response": ""
}
# Task: Determine if the user is new or continuing the conversation
1. Compare the current conversation with the previous conversation and if the user is new, assign "new" to response_template["response"] or if the user continues the previous conversation, then assign "continue" to response_template["response"]. Don't assign anything other than these.
2. Perform the task and return the json file.
\n 
"""
route_task_prompt = """
response_template = {
    "response": ""
}

tasks = [create a food plan, create a recipe, others]

# Task
1. If the conversation is related to any of the above tasks then assign the task's index to the response_template["response"]. Don't assign anything to it other than the mentioned. Note that index starts from 0.
2. Perform the task and return the json file.
"""
create_food_plan = """response_template = {
id : ""
user_input : "",
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
    
    
def new_or_continue_func(curr_conv, both_conv):
    out = call_ai(prompt = new_or_continue, inputs = both_conv)
    if out["response"] == "new":
        text = curr_conv
    else:
        text = both_conv
    return text


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
        self.item_id1 = "user_details"
        self.item_id2 = "user_conversations"
        
    def get_user_details(self, user_id):
        item = self.container.read_item(item = self.item_id1, partition_key = user_id)
        return str(item)
    
    async def get_prev_conversation(self, user_id):
        query = f"SELECT * FROM c WHERE c.user_id = '{user_id}' AND c.id = '{self.item_id2}'"
        items = list(self.container.query_items(
            query=query
        ))
        return str(items[0])
        
    def update_user_details(self, update_details):
        # Partition key and ID of the item to update
        partition_key = "1"
        item_id = "1"

        # Step 1: Read the item
        item = self.container.read_item(item=item_id, partition_key=partition_key)

        # Step 2: Modify the fields
        item['email'] = "new_email@example.com"
        item['status'] = "active"

        # Step 3: Replace the item
        self.container.replace_item(item=item_id, body=item)


class task_router:
    def __init__(self, prompts, route_task_prompt):
        self.prompts = prompts
        self.route_task_prompt = route_task_prompt
        
    def __call__(self, user_id, text):
        out = call_ai(prompt = self.route_task_prompt, inputs = text)
        idx = int(out["response"])
        
        if idx == 2:
            return call_ai.tts("Sorry! I can't help with that.")
        elif idx == 0:
            text = db_ops.get_user_details(user_id) + "\n\n" + text
            out = self.food_planner(self.prompts[idx], text)
            return out
        elif idx == 1:
            text = db_ops.get_user_details(user_id) + "\n\n" + text
            out = self.recipe_creator(self.prompts[idx], text)
            return out

    def food_planner(prompt, text):
        out = call_ai.ttt(prompt = prompt, inputs = text)
        out = call_ai.tts(out["response"])  # Returns mp3 file
        
        if out["update_details"] != "None":
            db_ops.update_user_details(out["update_details"])
        return out 
    
    def recipe_creator(prompt, text):
        out = call_ai(prompt = prompt, inputs = text)
        out = call_ai.tts(out["response"])  # Returns mp3 file
        return out


# Initialize AI and database
config = Config()
call_ai = AI(config.ttt_endpoint, config.ttt_key, config.stt_endpoint, config.stt_key, config.tts_endpoint, config.tts_key)
db_ops = db(config.DB_CONNECTION_STRING)   
route_task = task_router(prompts, route_task_prompt)


app = FastAPI()

@app.post('/call/{user_id}/{input}')        # input : mp3 format
async def call(user_id : int, mp3_file):
    # Converting speech-to-text and getting previous timestep conversation asynchronously
    text = await call_ai.stt(mp3_file)                 
    prev_conversation = await db_ops.get_prev_conversation(user_id) 
    
    # Checking if the user initiates new or continuing the conversation and processing it
    modified_text = "previous conversation :\n" + prev_conversation + "\n" + "current conversation:\n" + "user : " + text
    text = new_or_continue_func(text, modified_text)
    
    # Routing the conversation to the appropriate task
    out = route_task(user_id, text)    # Returns mp3 file
    return out
    
    