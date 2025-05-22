import dns
import time 
import asyncio
import pymongo
from fastapi import FastAPI


app = FastAPI()


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

verify_task = """
"""

task_router = """
response_template = {
    "response": ""
}

tasks = [create a food plan, manipulate ingredients, create a recipe]

# Task
1. If the conversation is related to any of the above tasks then assign the task's index to the response_template["response"]. Don't assign anything to it other than the mentioned. Note that index starts from 0.
2. Perform the task and return the json file.
"""

create_food_plan = """
response_template = {
id : ""
user_input : "",
final_response : "",
update_details : "None"
}

details = [
    "Weekly plan or a single daily plan",
    "Daily activity level (e.g., less active, moderately active, very active)",
    "Typical meal schedule (number of meals per day)",
    "Target weight or weight loss goal for example lose 5 kg in 2 months)"
  ]

tasks = {
"task_1" : "See through the <user_details> and <previous_conversations> and figure out whether the <user_details> contains the "details" to create a food plan. If "yes", then create a recipe plan with the "details" you have and provide the response as a value to the "final_response" key in the response template. The response must contain only the recipe plan, no other words should be present in it and don't use "\n" in your response instead use "   ". If "no", then ask the "details" to the user as a value to the "final_response" key in the response template. If asking the "details" to the user then follow the following steps: "Only questions should be present in your response. No other words should be present.", "Ask one question at a time.", "If options are available for your question then give options for your question like "what is you daily activity level? Is it less active or very active or moderately active".",
"task_2" : "See through the user_details and check if any of them is "None". If "no" then don't do anything and ignore the following steps. If "yes", then see through the conversation whether the user provided the details for the user_details which has "None". If "yes", then create a mongodb atlas command to update details for the user id and assign the command as a value to the "update_details" key in the "response_template". If "no", then don't don't do anything."
}
Perform the tasks and return the json file."""

manipulate_ingredients = """
"""

create_recipe = """
"""

prompts = [create_food_plan, manipulate_ingredients, create_recipe]

# Functions
async def get_prev_conversation(user_id):
    """
    Retrieves the latest conversation for a given user ID
    by sorting on date and timestep in descending order.
    """
    client = pymongo.MongoClient("mongodb+srv://<db_username>:<db_password>@<clusterName>.mongodb.net/?retryWrites=true&w=majority")
    db = client.user_data
    
    collection = db.conversations
    latest_conversation = collection.find(
        {"id": user_id},
        sort=[("date", pymongo.DESCENDING), ("timestep", pymongo.DESCENDING)],
        limit=1
    )
    
    result = list(latest_conversation)
    if result:
        return result[0].get("conversations")
    else:
        return None
    
def call_ai():
    out = "" # json file
    return out

def new_or_continue_func(curr_conv, both_conv):
    out = call_ai(prompt = new_or_continue, inputs = both_conv)
    if out["response"] == "new":
        text = curr_conv
    else:
        text = both_conv
    return text

def task_router_func(text):
    out = call_ai(prompt = task_router, inputs = text)
    idx = int(out["response"])
    prompt = prompts[idx]
    return prompt
   
async def stt(mp3):
    return await call_ai(mp3)

@app.post('/call/{user_id}/{input}')        # input : mp3 format
async def call(user_id : int, input):
    text = await stt(input)                 
    prev_conversation = await get_prev_conversation(user_id)    
    modified_text = "previous conversation :\n" + prev_conversation + "\n" + "current conversation:\n" + "user : " + text
    text = new_or_continue_func(text, modified_text)
    prompt = task_router(text)
    out = call_ai(prompt = prompt, inputs = text)
    
    