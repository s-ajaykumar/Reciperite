new_or_continue = """
response_template = {
    "response": ""
}
# Task: Determine if the user is new or continuing the conversation
1. Compare the current conversation with the previous conversation and if the user initiates a new conversation, then assign "new" to response_template["response"] or if the user continues the previous conversation, then assign "continue" to response_template["response"]. Don't assign anything other than these.
2. Perform the task and return the json file.
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