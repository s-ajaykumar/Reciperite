from fastapi import FastAPI
from pydantic import BaseModel

class TaskRequest(BaseModel):
    input : str
    
class TaskResponse(BaseModel):
    response : str
    
app = FastAPI()

@app.post("/route_task", response_model = TaskResponse)
def route_task(request : TaskRequest):
    return {"response": f"Hii {request.input}"}