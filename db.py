import os
import uuid
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, PartitionKey

load_dotenv()

DB_ENDPOINT = os.environ["DB_CONNECTION_STRING"]

client = CosmosClient.from_connection_string(DB_ENDPOINT)

# Example: Access a database and container
database = client.get_database_client("Receipe")

container = database.get_container_client("users")

query = "SELECT * FROM c WHERE c.user_id = 'c09b219b-16b6-46f4-a34e-e73b2b8ada62' AND c.id != 'user_details' ORDER BY c.id DESC"
items = list(container.query_items(
    query=query
))
for item in items:
    date = item['id']
    print(date)
    [print(i) for i in item['conversations']]
    
       
user_ids = ["ef6d4915-ef45-4491-b604-fc729413af80", "c09b219b-16b6-46f4-a34e-e73b2b8ada62"] 
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