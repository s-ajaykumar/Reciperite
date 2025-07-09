import os
import uuid
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey
import time

load_dotenv()

DB_ENDPOINT = os.environ["DB_CONNECTION_STRING"]

client = CosmosClient.from_connection_string(DB_ENDPOINT)

# Example: Access a database and container
database = client.get_database_client("Receipe")

container = database.get_container_client("users")

# Update conversation
'''t1 = time.time()
item = container.read_item(item = '20250523T192100Z', partition_key = 'ef6d4915-ef45-4491-b604-fc729413af80')
item['conversations'].extend(["user: nothiing\n\n"])  
container.replace_item(item = '20250523T192100Z', body = item)
item = container.read_item(item = '20250523T192100Z', partition_key = 'ef6d4915-ef45-4491-b604-fc729413af80')
t2 = time.time()
print(item)
print(f"Time taken for fetching previus conversation- {(t2 - t1)*1000:4f} ms")'''


# Get previous conversation
t1 = time.time()
query = f"SELECT * FROM c WHERE c.user_id = '001' AND c.id != 'user_details' ORDER BY c.id DESC OFFSET 0 LIMIT 1"
items = list(container.query_items(
    query = query
))
t2 = time.time()
print(''.join(items[0]['conversations']))
print(items)
print(f"Time taken for fetching previus conversation- {(t2 - t1)*1000:4f} ms")


'''item = container.read_item(item='user_details', partition_key='001')
print(item['details'])'''


# Query items
'''t1 = time.time()
query = "SELECT * FROM c WHERE c.user_id = '001' AND c.item_id != 'user_details'"
items = list(container.query_items(
    query=query
))
t2 = time.time()
print(t2-t1*1000, "  ms")
print(items)  # Returns the last conversation and its id'''

# Read an item
'''item = container.read_item(item = 'user_details', partition_key = '001')
print(item['details'])'''



'''update_item = {
            "name": "Chandru",
            "gender": "female",
            "age": 23,
            "weight": "40Kgs",
            "height": "150cms",
            "country": "India",
            "state": "Tamil Nadu",
            "diet": "Non - Vegetarian",
            "activity_level": "more active",
            "meal_schedule": 3
            }
for key, value in update_item.items():
    item['details'][key] = value
print(item['details'])
item = container.replace_item(item = 'user_details', body = item)'''


'''user_ids =      ["001"]            #["ef6d4915-ef45-4491-b604-fc729413af80", "c09b219b-16b6-46f4-a34e-e73b2b8ada62"] 
items = [
    {
        "id": "user_details",
        "user_id": user_ids[0],
        "details" : {
            "name": "superman",
            "gender": "female",
            "age": 22,
            "weight": "40Kgs",
            "height": "150cms",
            "country": "India",
            "state": "Tamil Nadu",
            "diet": "Non - Vegetarian",
            "activity_level": "more active",
            "meal_schedule": 3
            }
    }   
]
for item in items:
    container.create_item(body = item)'''
   

'''items = [
    {
        "id" : "20250523T181100Z",     # timestamp
        "user_id" : user_ids[0],
        "conversations" : ["user : Tell me a recipe for pasta\n", "AI : Sure! Here is a simple recipe for pasta: ...\n"]
    },
    {
        "id" : "20250523T192100Z",
        "user_id" : user_ids[0],
        "conversations" : ["user : Tell me a recipe for maiyonisee\n", "AI : Sure! Here is a simple recipe for maiyonisse: ...\n"]
    },
    {
        "id" : "20250522T192100Z",
        "user_id" : user_ids[1],
        "conversations" : ["user : gie me a food plan to reduce weight\n", "AI : Sure! How much weight ot loss\n", "user : 10kgs in 2 months\n"]  
    },
    {
        "id" : "20250523T192100Z",
        "user_id" : user_ids[1],
        "conversations" : ["user : gie me a food plan to gain weight\n", "AI : Sure! How much weight to gain\n", "user : 10kgs in 2 months\n"]
        
    }
]

for item in items:
    container.create_item(body = item)'''
    
    
    
'''user_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
with open("user_ids.txt", "w") as f:
    for user_id in user_ids:
        f.write(user_id + "\n")'''
        
    