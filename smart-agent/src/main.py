import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import random

app = FastAPI()

is_crashed = False

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
async def process_query(request: QueryRequest):
    global is_crashed
    if is_crashed:
        await asyncio.sleep(10)
        raise Exception("Agent is crashed")
        
    print(f"[SmartAgent] Received query: {request.query}")
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
    print(f"[SmartAgent] Finished query after {delay:.2f}s")
    
    return {
        "agent_id": "smart-agent",
        "response": response_text,
        "delay": delay
    }

@app.get("/health")
async def health():
    if is_crashed:
        raise HTTPException(status_code=500, detail="crashed")
    return {"status": "ok", "service": "smart-agent"}

@app.post("/simulate-crash")
async def simulate_crash():
    global is_crashed
    is_crashed = True
    print(f"[SmartAgent] CRASH SIMULATED. Will fail health checks.")
    return {"status": "crashed"}

@app.post("/recover")
async def recover():
    global is_crashed
    is_crashed = False
    print(f"[SmartAgent] RECOVERED. Resuming normal operation.")
    return {"status": "recovered"}
