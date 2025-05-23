
import httpx
from fastapi import FastAPI


link = "http://127.0.0.1:8000/route_task" 

class a:
    def __init__(self):
        pass
        
    async def f(self):
        async with httpx.AsyncClient() as client:
            out = await client.post(link, json = {'input' : 'ajay'})
            return out.json()
aa = a()

async def b():
    async with httpx.AsyncClient() as client:
        out =  await client.post(link, json = {'input' : 'vikram'})
        return out.json()
    
app2 = FastAPI()
@app2.post("/c")
async def c():
    out = await aa.f()
    out2 = await b()
    out = out.get("response", "") + "\n\n" + out2.get("response", "")
    print(out)