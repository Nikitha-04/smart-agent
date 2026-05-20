import asyncio
import httpx
import sys
import os
from fastapi import FastAPI
from pydantic import BaseModel
import time
import random

app = FastAPI()

ROUTER_URL = "http://localhost:9000"

AGENT_PORT = int(os.environ.get("PORT", 8001))
MODEL_NAME = os.environ.get("MODEL_NAME", "Default Model")
INSTANCE_NUM = os.environ.get("INSTANCE_NUM", "1")
API_KEY = os.environ.get("OPENAI_API_KEY", "")

AGENT_URL = f"http://localhost:{AGENT_PORT}"
AGENT_ID = f"{MODEL_NAME} (Inst {INSTANCE_NUM})"

is_crashed = False

class QueryRequest(BaseModel):
    query: str

@app.on_event("startup")
async def startup_event():
    print(f"[{AGENT_ID}] Starting up on {AGENT_URL}...")
    if not API_KEY:
        print(f"[{AGENT_ID}] WARNING: No OpenAI API Key found!")
    asyncio.create_task(heartbeat_loop())

async def heartbeat_loop():
    global is_crashed
    async with httpx.AsyncClient() as client:
        while True:
            if not is_crashed:
                try:
                    await client.post(f"{ROUTER_URL}/heartbeat", json={
                        "agent_id": AGENT_ID,
                        "url": AGENT_URL
                    }, timeout=2.0)
                except Exception as e:
                    print(f"[{AGENT_ID}] Failed to heartbeat to router: {e}")
            await asyncio.sleep(2)  # Heartbeat every 2 seconds

@app.post("/query")
async def process_query(request: QueryRequest):
    global is_crashed
    if is_crashed:
        await asyncio.sleep(10)
        raise Exception("Agent is crashed")
        
    print(f"[{AGENT_ID}] Received query: {request.query}")
    
    start_time = time.time()
    
    # --- SIMULATION MODE ---
    # Simulate processing time based on query length (longer query = slightly longer time)
    base_delay = random.uniform(1.0, 3.5)
    await asyncio.sleep(base_delay)
    
    # Generate a realistic-looking mock response
    mock_responses = [
        f"Here is a detailed response to your query about '{request.query[:20]}...'",
        "I have processed your request successfully using my local memory allocation.",
        "Here is the code/information you requested. (Simulated AI Output)",
        "Task completed. My CPU and RAM usage remained stable during this operation."
    ]
    response_text = random.choice(mock_responses)
    
    delay = time.time() - start_time
    print(f"[{AGENT_ID}] Finished query after {delay:.2f}s")
    
    return {
        "agent_id": AGENT_ID,
        "response": response_text,
        "delay": delay
    }

@app.get("/health")
async def health():
    if is_crashed:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="crashed")
    return {"status": "ok", "agent_id": AGENT_ID}

@app.post("/simulate-crash")
async def simulate_crash():
    global is_crashed
    is_crashed = True
    print(f"[{AGENT_ID}] CRASH SIMULATED. Stopping heartbeats.")
    return {"status": "crashed"}

@app.post("/recover")
async def recover():
    global is_crashed
    is_crashed = False
    print(f"[{AGENT_ID}] RECOVERED. Resuming heartbeats.")
    return {"status": "recovered"}
