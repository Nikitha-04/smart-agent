import asyncio
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
import time
import random
from typing import Dict, List

app = FastAPI()

# --- Global State & Metrics ---
agents: Dict[str, dict] = {
    "GPT-3.5 Turbo (Inst 1)": {
        "url": "http://testserver/agent/1",
        "last_heartbeat": time.time(),
        "active_connections": 0,
        "total_handled": 0
    },
    "GPT-3.5 Turbo (Inst 2)": {
        "url": "http://testserver/agent/2",
        "last_heartbeat": time.time(),
        "active_connections": 0,
        "total_handled": 0
    },
    "GPT-3.5 Turbo (Inst 3)": {
        "url": "http://testserver/agent/3",
        "last_heartbeat": time.time(),
        "active_connections": 0,
        "total_handled": 0
    }
}

is_crashed = {
    "GPT-3.5 Turbo (Inst 1)": False,
    "GPT-3.5 Turbo (Inst 2)": False,
    "GPT-3.5 Turbo (Inst 3)": False
}

query_history: List[dict] = []  # Keep last 50 queries

router_metrics = {
    "total_requests": 0,
    "successful": 0,
    "failed": 0,
    "by_strategy": {"round_robin": 0, "least_connections": 0, "random": 0}
}

class QueryRequest(BaseModel):
    query: str

class BurstRequest(BaseModel):
    strategy: str
    count: int = 15

def update_heartbeats():
    now = time.time()
    for agent_id, data in agents.items():
        if not is_crashed.get(agent_id, False):
            data["last_heartbeat"] = now

def get_healthy_agents():
    update_heartbeats()
    now = time.time()
    healthy = []
    for agent_id, data in agents.items():
        if now - data["last_heartbeat"] <= 30.0:
            healthy.append(agent_id)
    return healthy

# --- Routing Strategies ---
round_robin_counter = 0

def select_agent_round_robin(healthy_agents):
    global round_robin_counter
    if not healthy_agents:
        return None
    agent_id = healthy_agents[round_robin_counter % len(healthy_agents)]
    round_robin_counter += 1
    return agent_id

def select_agent_least_connections(healthy_agents):
    if not healthy_agents:
        return None
    return min(healthy_agents, key=lambda a: agents[a]["active_connections"])

def select_agent_random(healthy_agents):
    if not healthy_agents:
        return None
    return random.choice(healthy_agents)

# --- Core Routing Logic ---
async def execute_query(query: str, strategy: str):
    router_metrics["total_requests"] += 1
    router_metrics["by_strategy"][strategy] = router_metrics["by_strategy"].get(strategy, 0) + 1
    start_time = time.time()
    
    healthy_agents = get_healthy_agents()
    if not healthy_agents:
        router_metrics["failed"] += 1
        record_history(query, strategy, "None", False, 0.0, "No healthy agents available")
        raise HTTPException(status_code=503, detail="No healthy agents available")

    if strategy == "round_robin":
        selected_id = select_agent_round_robin(healthy_agents)
    elif strategy == "random":
        selected_id = select_agent_random(healthy_agents)
    else:  # default least_connections
        selected_id = select_agent_least_connections(healthy_agents)

    agent_data = agents[selected_id]
    agent_url = agent_data["url"]

    # Forward the request internally (in-process)
    agent_data["active_connections"] += 1
    try:
        async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.post(f"{agent_url}/query", json={"query": query}, timeout=60.0)
            response.raise_for_status()
            res_data = response.json()
            
            # Update metrics
            agent_data["total_handled"] += 1
            router_metrics["successful"] += 1
            elapsed = time.time() - start_time
            
            record_history(query, strategy, selected_id, True, elapsed, res_data.get("response"))
            return res_data
            
    except Exception as e:
        agent_data["last_heartbeat"] = 0  # circuit breaker
        router_metrics["failed"] += 1
        elapsed = time.time() - start_time
        record_history(query, strategy, selected_id, False, elapsed, str(e))
        raise HTTPException(status_code=502, detail=f"Bad Gateway: {str(e)}")
    finally:
        agent_data["active_connections"] -= 1

def record_history(query, strategy, agent_id, success, time_taken, response):
    query_history.insert(0, {
        "timestamp": time.strftime("%H:%M:%S"),
        "query": query,
        "strategy": strategy,
        "agent": agent_id,
        "success": success,
        "time_taken": round(time_taken, 2),
        "response": response
    })
    if len(query_history) > 50:
        query_history.pop()

@app.post("/query")
async def route_query(request: QueryRequest, strategy: str = "least_connections"):
    return await execute_query(request.query, strategy)

@app.post("/burst")
async def burst_test(req: BurstRequest, background_tasks: BackgroundTasks):
    """Fires N concurrent requests internally to demonstrate load balancing under stress."""
    async def run_burst():
        tasks = []
        for i in range(req.count):
            tasks.append(execute_query(f"Burst Query #{i+1}", req.strategy))
        await asyncio.gather(*tasks, return_exceptions=True)
        
    background_tasks.add_task(run_burst)
    return {"message": f"Burst test started with {req.count} queries using {req.strategy}."}

# --- Proxy to Agent Controls ---
@app.post("/agent-control/{agent_id}/{action}")
async def control_agent(agent_id: str, action: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    url = agents[agent_id]["url"]
    
    if action not in ["simulate-crash", "recover"]:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    try:
        async with httpx.AsyncClient(app=app, base_url="http://testserver") as client:
            await client.post(f"{url}/{action}", timeout=2.0)
            return {"status": "success", "action": action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Dashboard APIs & HTML ---
@app.get("/status")
async def get_status():
    healthy_agents = get_healthy_agents()
    agent_list = []
    
    for agent_id, data in agents.items():
        agent_list.append({
            "id": agent_id,
            "url": data["url"],
            "is_healthy": agent_id in healthy_agents,
            "active_connections": data["active_connections"],
            "total_handled": data["total_handled"]
        })
        
    return {
        "metrics": router_metrics,
        "agents": agent_list,
        "history": query_history
    }

# --- Virtual Agent Endpoint Logic (from agent.py) ---
@app.post("/agent/{instance_id}/query")
async def virtual_agent_query(instance_id: str, request: QueryRequest):
    agent_name = f"GPT-3.5 Turbo (Inst {instance_id})"
    if is_crashed.get(agent_name, False):
        await asyncio.sleep(1.0)
        raise HTTPException(status_code=500, detail="Agent is crashed")
        
    start_time = time.time()
    
    # Simulate processing time based on query length (longer query = slightly longer time)
    base_delay = random.uniform(1.0, 3.5)
    await asyncio.sleep(base_delay)
    
    mock_responses = [
        f"Here is a detailed response to your query about '{request.query[:20]}...'",
        "I have processed your request successfully using my local memory allocation.",
        "Here is the code/information you requested. (Simulated AI Output)",
        "Task completed. My CPU and RAM usage remained stable during this operation."
    ]
    response_text = random.choice(mock_responses)
    
    delay = time.time() - start_time
    
    return {
        "agent_id": agent_name,
        "response": response_text,
        "delay": delay
    }

@app.post("/agent/{instance_id}/simulate-crash")
async def virtual_agent_crash(instance_id: str):
    agent_name = f"GPT-3.5 Turbo (Inst {instance_id})"
    is_crashed[agent_name] = True
    return {"status": "crashed"}

@app.post("/agent/{instance_id}/recover")
async def virtual_agent_recover(instance_id: str):
    agent_name = f"GPT-3.5 Turbo (Inst {instance_id})"
    is_crashed[agent_name] = False
    return {"status": "recovered"}

@app.get("/agent/{instance_id}/health")
async def virtual_agent_health(instance_id: str):
    agent_name = f"GPT-3.5 Turbo (Inst {instance_id})"
    if is_crashed.get(agent_name, False):
        raise HTTPException(status_code=500, detail="crashed")
    return {"status": "ok", "agent_id": agent_name}

@app.get("/")
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Agent — Serverless Load Balancer</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            *{margin:0;padding:0;box-sizing:border-box;}
            :root{
                --bg:#04070f;
                --surface:#0d1526;
                --surface2:#111d35;
                --card:#141f38;
                --border:#1e2f52;
                --primary:#4f8eff;
                --primary-glow:rgba(79,142,255,0.35);
                --cyan:#00d4ff;
                --purple:#a78bfa;
                --green:#10d98e;
                --orange:#ff7b3a;
                --red:#ff4d6d;
                --text:#e8f0ff;
                --muted:#6b82a8;
            }
            body.light{
                --bg:linear-gradient(135deg,#e0f2fe 0%,#f0e6ff 50%,#fce7f3 100%);
                --surface:rgba(255,255,255,0.7);
                --surface2:rgba(255,255,255,0.5);
                --card:rgba(255,255,255,0.9);
                --border:rgba(99,102,241,0.2);
                --primary:#6366f1;
                --cyan:#0ea5e9;
                --purple:#a855f7;
                --green:#10b981;
                --red:#ef4444;
                --text:#1e1b4b;
                --muted:#6b7280;
            }
            body.light{background:linear-gradient(135deg,#e0f2fe 0%,#f0e6ff 50%,#fce7f3 100%) !important;}
            body.light .bg-grid{background-image:linear-gradient(rgba(99,102,241,0.06) 1px,transparent 1px),linear-gradient(90deg,rgba(99,102,241,0.06) 1px,transparent 1px);}
            body.light .orb1{background:radial-gradient(circle,rgba(168,85,247,0.2),transparent 70%);}
            body.light .orb2{background:radial-gradient(circle,rgba(14,165,233,0.15),transparent 70%);}
            body.light .orb3{background:radial-gradient(circle,rgba(236,72,153,0.12),transparent 70%);}
            body.light .brand-text h1{background:linear-gradient(135deg,#6366f1 0%,#a855f7 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
            body.light .logo-ring{background:linear-gradient(135deg,#6366f1,#a855f7);box-shadow:0 0 30px rgba(99,102,241,0.5);}
            body.light .metric-card{background:rgba(255,255,255,0.85);border:1px solid rgba(99,102,241,0.2);backdrop-filter:blur(10px);}
            body.light .metric-card:hover{box-shadow:0 20px 40px rgba(99,102,241,0.2);}
            body.light .metric-card.total .metric-value{color:#6366f1;}
            body.light .metric-card.success .metric-value{color:#10b981;}
            body.light .metric-card.failed .metric-value{color:#ef4444;}
            body.light .metric-card.total::before{background:linear-gradient(90deg,#6366f1,#a855f7);}
            body.light .card{background:rgba(255,255,255,0.85);border:1px solid rgba(99,102,241,0.15);backdrop-filter:blur(10px);}
            body.light .controls-card{background:rgba(255,255,255,0.85);border:1px solid rgba(99,102,241,0.15);backdrop-filter:blur(10px);}
            body.light .history-card{background:rgba(255,255,255,0.85);border:1px solid rgba(99,102,241,0.15);backdrop-filter:blur(10px);}
            body.light .agent-card{background:rgba(255,255,255,0.6);border:1px solid rgba(99,102,241,0.15);}
            body.light .agent-card:hover{background:rgba(255,255,255,0.9);}
            body.light input,body.light select{background:rgba(255,255,255,0.8);border-color:rgba(99,102,241,0.3);color:#1e1b4b;}
            body.light .strategy-info{background:rgba(99,102,241,0.08);}
            body.light th{background:rgba(99,102,241,0.08);color:#6b7280;}
            body.light tr:hover td{background:rgba(99,102,241,0.05);}
            body.light code{background:rgba(99,102,241,0.1);color:#6366f1;}
            body.light .btn-primary{background:linear-gradient(135deg,#6366f1,#a855f7);}
            body.light .live-badge{background:rgba(16,185,129,0.15);border-color:rgba(16,185,129,0.4);}
            body.light .theme-toggle{background:rgba(255,255,255,0.7);border-color:rgba(99,102,241,0.3);}
            /* Theme toggle */
            .theme-toggle{background:var(--surface);border:1px solid var(--border);border-radius:50px;padding:8px 16px;cursor:pointer;font-size:1rem;transition:all 0.3s;display:flex;align-items:center;gap:6px;color:var(--text);font-family:inherit;font-weight:600;font-size:0.82rem;}
            .theme-toggle:hover{background:var(--surface2);}
            .header-right{display:flex;align-items:center;gap:12px;}
            body{font-family:'Plus Jakarta Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}

            /* Animated background */
            .bg-grid{position:fixed;inset:0;background-image:linear-gradient(rgba(79,142,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(79,142,255,0.03) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0;}
            .orb{position:fixed;border-radius:50%;filter:blur(100px);pointer-events:none;z-index:0;}
            .orb1{width:600px;height:600px;background:radial-gradient(circle,rgba(79,142,255,0.12),transparent 70%);top:-200px;right:-200px;animation:float1 8s ease-in-out infinite;}
            .orb2{width:500px;height:500px;background:radial-gradient(circle,rgba(0,212,255,0.08),transparent 70%);bottom:-100px;left:-100px;animation:float2 10s ease-in-out infinite;}
            .orb3{width:400px;height:400px;background:radial-gradient(circle,rgba(167,139,250,0.07),transparent 70%);top:40%;left:40%;animation:float3 12s ease-in-out infinite;}
            @keyframes float1{0%,100%{transform:translate(0,0);}50%{transform:translate(-30px,30px);}}
            @keyframes float2{0%,100%{transform:translate(0,0);}50%{transform:translate(40px,-20px);}}
            @keyframes float3{0%,100%{transform:translate(0,0);}50%{transform:translate(-20px,-40px);}}

            main{position:relative;z-index:1;padding:30px 40px;}

            /* ── HEADER ── */
            header{display:flex;justify-content:space-between;align-items:center;margin-bottom:40px;}
            .brand{display:flex;align-items:center;gap:16px;}
            .logo-ring{width:56px;height:56px;border-radius:16px;background:linear-gradient(135deg,#4f8eff,#00d4ff);display:flex;align-items:center;justify-content:center;font-size:1.5rem;box-shadow:0 0 30px rgba(79,142,255,0.5);animation:pulse-logo 3s ease-in-out infinite;}
            @keyframes pulse-logo{0%,100%{box-shadow:0 0 30px rgba(79,142,255,0.5);}50%{box-shadow:0 0 50px rgba(79,142,255,0.8),0 0 80px rgba(0,212,255,0.3);}}
            .brand-text h1{font-size:1.8rem;font-weight:800;background:linear-gradient(135deg,#fff 30%,#4f8eff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1;}
            .brand-text .tagline{font-size:0.8rem;color:var(--muted);margin-top:2px;}
            .brand-text .sub-tagline{font-size:0.72rem;color:var(--primary);opacity:0.8;}
            .live-badge{display:flex;align-items:center;gap:8px;background:rgba(16,217,142,0.1);border:1px solid rgba(16,217,142,0.3);padding:8px 16px;border-radius:50px;font-size:0.82rem;color:var(--green);}
            .live-dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:blink 1.4s ease-in-out infinite;}
            @keyframes blink{0%,100%{opacity:1;}50%{opacity:0.2;}}

            /* ── METRIC CARDS ── */
            .metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:30px;}
            .metric-card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:24px;position:relative;overflow:hidden;transition:transform 0.3s,box-shadow 0.3s;}
            .metric-card:hover{transform:translateY(-4px);box-shadow:0 20px 40px rgba(0,0,0,0.4);}
            .metric-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
            .metric-card.total::before{background:linear-gradient(90deg,#4f8eff,#00d4ff);}
            .metric-card.success::before{background:linear-gradient(90deg,#10d98e,#4f8eff);}
            .metric-card.failed::before{background:linear-gradient(90deg,#ff4d6d,#ff7b3a);}
            .metric-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;margin-bottom:16px;}
            .metric-card.total .metric-icon{background:rgba(79,142,255,0.15);}
            .metric-card.success .metric-icon{background:rgba(16,217,142,0.15);}
            .metric-card.failed .metric-icon{background:rgba(255,77,109,0.15);}
            .metric-label{font-size:0.78rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}
            .metric-value{font-size:2.8rem;font-weight:800;line-height:1;}
            .metric-card.total .metric-value{color:#4f8eff;}
            .metric-card.success .metric-value{color:#10d98e;}
            .metric-card.failed .metric-value{color:#ff4d6d;}

            /* ── MAIN GRID ── */
            .grid{display:grid;grid-template-columns:1.4fr 1fr;gap:24px;margin-bottom:24px;}
            .card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:24px;}
            .card-title{font-size:0.85rem;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin-bottom:20px;display:flex;align-items:center;gap:8px;}
            .card-title span{width:6px;height:6px;border-radius:50%;background:var(--primary);display:inline-block;}

            /* ── AGENT CARDS ── */
            .agents-grid{display:flex;flex-direction:column;gap:12px;}
            .agent-card{background:var(--surface2);border:1px solid var(--border);border-radius:14px;padding:16px 20px;display:flex;align-items:center;gap:16px;transition:all 0.3s;}
            .agent-card.healthy{border-left:3px solid var(--green);}
            .agent-card.dead{border-left:3px solid var(--red);opacity:0.7;}
            .agent-card:hover{background:var(--surface);transform:translateX(4px);}
            .agent-avatar{width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;position:relative;}
            .agent-avatar.healthy{background:linear-gradient(135deg,rgba(16,217,142,0.2),rgba(79,142,255,0.2));border:1px solid rgba(16,217,142,0.3);}
            .agent-avatar.dead{background:rgba(255,77,109,0.1);border:1px solid rgba(255,77,109,0.2);}
            .agent-pulse{position:absolute;inset:-3px;border-radius:14px;border:2px solid var(--green);animation:agent-ring 2s ease-in-out infinite;opacity:0.5;}
            @keyframes agent-ring{0%,100%{opacity:0.5;transform:scale(1);}50%{opacity:0;transform:scale(1.15);}}
            .agent-info{flex:1;}
            .agent-name{font-weight:700;font-size:0.92rem;margin-bottom:4px;}
            .agent-meta{font-size:0.75rem;color:var(--muted);}
            .agent-stats{display:flex;gap:16px;align-items:center;}
            .stat-pill{text-align:center;}
            .stat-pill .val{font-size:1.1rem;font-weight:800;color:var(--primary);}
            .stat-pill .lbl{font-size:0.65rem;color:var(--muted);text-transform:uppercase;}
            .agent-btn{padding:7px 14px;border-radius:8px;border:none;font-size:0.75rem;font-weight:700;cursor:pointer;transition:all 0.2s;font-family:inherit;}
            .btn-crash{background:rgba(255,77,109,0.15);color:#ff4d6d;border:1px solid rgba(255,77,109,0.3);}
            .btn-crash:hover{background:rgba(255,77,109,0.3);}
            .btn-recover{background:rgba(16,217,142,0.15);color:#10d98e;border:1px solid rgba(16,217,142,0.3);}
            .btn-recover:hover{background:rgba(16,217,142,0.3);}
            .badge{padding:3px 10px;border-radius:50px;font-size:0.68rem;font-weight:700;}
            .badge-ok{background:rgba(16,217,142,0.15);color:var(--green);}
            .badge-dead{background:rgba(255,77,109,0.15);color:var(--red);}

            /* ── CHART ── */
            .chart-wrap{position:relative;height:180px;}

            /* ── CONTROLS PANEL ── */
            .controls-card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:24px;}
            label{display:block;font-size:0.78rem;color:var(--muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;}
            input,select{width:100%;padding:11px 14px;border-radius:10px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-family:inherit;font-size:0.88rem;outline:none;transition:border 0.2s;}
            input:focus,select:focus{border-color:var(--primary);}
            .send-row{display:flex;gap:10px;align-items:flex-end;}
            .send-row input{flex:1;}
            .btn{padding:11px 20px;border-radius:10px;border:none;font-weight:700;cursor:pointer;transition:all 0.2s;font-family:inherit;color:white;font-size:0.88rem;}
            .btn-primary{background:linear-gradient(135deg,#4f8eff,#0077ff);box-shadow:0 4px 20px rgba(79,142,255,0.4);}
            .btn-primary:hover{box-shadow:0 6px 30px rgba(79,142,255,0.7);transform:translateY(-2px);}
            .btn-primary:disabled{opacity:0.5;transform:none;cursor:not-allowed;}
            .btn-burst{background:linear-gradient(135deg,#ff7b3a,#ff4d6d);box-shadow:0 4px 20px rgba(255,77,109,0.4);width:100%;margin-top:12px;padding:13px;font-size:0.92rem;}
            .btn-burst:hover{box-shadow:0 6px 30px rgba(255,77,109,0.7);transform:translateY(-2px);}
            .divider{border:none;border-top:1px solid var(--border);margin:20px 0;}
            .strategy-info{font-size:0.78rem;color:var(--muted);margin-top:8px;padding:10px;background:var(--surface);border-radius:8px;line-height:1.5;}

            /* ── HISTORY ── */
            .history-card{background:var(--card);border:1px solid var(--border);border-radius:20px;overflow:hidden;}
            .history-header{padding:20px 24px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;}
            .history-scroll{max-height:380px;overflow-y:auto;}
            .history-scroll::-webkit-scrollbar{width:4px;}
            .history-scroll::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px;}
            table{width:100%;border-collapse:collapse;}
            th{padding:12px 16px;text-align:left;font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px;background:var(--surface2);position:sticky;top:0;}
            td{padding:13px 16px;font-size:0.83rem;border-bottom:1px solid rgba(30,47,82,0.5);}
            tr:hover td{background:rgba(79,142,255,0.04);}
            .row-ok td:first-child{border-left:2px solid var(--green);}
            .row-fail td:first-child{border-left:2px solid var(--red);}
            .resp-cell{max-height:60px;overflow-y:auto;font-size:0.78rem;color:var(--muted);}
            code{background:var(--surface);padding:2px 8px;border-radius:5px;font-size:0.78rem;color:var(--cyan);}

            /* ── FLOATING PARTICLES (decorative) ── */
            .particle{position:fixed;width:3px;height:3px;border-radius:50%;background:rgba(79,142,255,0.5);pointer-events:none;z-index:0;animation:drift linear infinite;}
            @keyframes drift{0%{transform:translateY(100vh) translateX(0);opacity:0;}10%{opacity:1;}90%{opacity:1;}100%{transform:translateY(-100px) translateX(80px);opacity:0;}}

            /* ── WORKING ANIMATION ── */
            @keyframes working{0%,100%{box-shadow:0 0 0 0 rgba(79,142,255,0.5);}50%{box-shadow:0 0 0 8px rgba(79,142,255,0);}}
        </style>
    </head>
    <body>
        <div class="bg-grid"></div>
        <div class="orb orb1"></div>
        <div class="orb orb2"></div>
        <div class="orb orb3"></div>

        <main>
            <!-- HEADER -->
            <header>
                <div class="brand">
                    <div class="logo-ring">🧠</div>
                    <div class="brand-text">
                        <h1>Smart Agent</h1>
                        <div class="tagline">Serverless Load Balancer</div>
                        <div class="sub-tagline">Multiple virtual AI agents working simultaneously to solve every problem</div>
                    </div>
                </div>
                <div class="header-right">
                    <button class="theme-toggle" onclick="toggleTheme()" id="theme-btn">🌙 Dark Mode</button>
                    <div class="live-badge">
                        <div class="live-dot"></div>
                        All Systems Live
                    </div>
                </div>
            </header>

            <!-- METRICS -->
            <div class="metrics">
                <div class="metric-card total">
                    <div class="metric-icon">📊</div>
                    <div class="metric-label">Total Requests</div>
                    <div class="metric-value" id="m-total">0</div>
                </div>
                <div class="metric-card success">
                    <div class="metric-icon">✅</div>
                    <div class="metric-label">Successful</div>
                    <div class="metric-value" id="m-success">0</div>
                </div>
                <div class="metric-card failed">
                    <div class="metric-icon">⚠️</div>
                    <div class="metric-label">Failed</div>
                    <div class="metric-value" id="m-failed">0</div>
                </div>
            </div>

            <!-- MAIN GRID -->
            <div class="grid">
                <!-- LEFT: Agents + Chart -->
                <div>
                    <div class="card" style="margin-bottom:20px;">
                        <div class="card-title"><span></span>Active Agent Pool</div>
                        <div class="agents-grid" id="agents-grid">
                            <p style="color:var(--muted);font-size:0.85rem;text-align:center;padding:20px;">Waiting for agents to register...</p>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-title"><span></span>Load Distribution</div>
                        <div class="chart-wrap">
                            <canvas id="distChart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- RIGHT: Controls -->
                <div class="controls-card">
                    <div class="card-title"><span></span>Mission Control</div>

                    <form id="q-form">
                        <div style="margin-bottom:14px;">
                            <label>Your Query</label>
                            <input type="text" id="q-input" placeholder="Ask anything..." required>
                        </div>
                        <div style="margin-bottom:14px;">
                            <label>Routing Strategy</label>
                            <select id="strategy">
                                <option value="least_connections">⚡ Least Connections (Recommended)</option>
                                <option value="round_robin">🔄 Round Robin</option>
                                <option value="random">🎲 Random</option>
                            </select>
                        </div>
                        <div id="strategy-info" class="strategy-info">⚡ Routes to the agent with the lowest active workload for maximum speed.</div>
                        <button type="submit" class="btn btn-primary" id="btn-send" style="width:100%;margin-top:14px;">Send to Smart Agent 🚀</button>
                    </form>

                    <hr class="divider">

                    <div class="card-title"><span></span>Burst Test</div>
                    <p style="font-size:0.8rem;color:var(--muted);margin-bottom:12px;line-height:1.6;">Fire 15 simultaneous queries to visually prove load balancing. Watch all agents light up in real-time!</p>
                    <select id="burst-strategy" style="margin-bottom:4px;">
                        <option value="least_connections">⚡ Least Connections</option>
                        <option value="round_robin">🔄 Round Robin</option>
                        <option value="random">🎲 Random</option>
                    </select>
                    <button class="btn btn-burst" onclick="runBurst()">🔥 Fire 15 Agents Now!</button>
                </div>
            </div>

            <!-- HISTORY TABLE -->
            <div class="history-card" style="margin-bottom:24px;">
                <div class="history-header">
                    <div class="card-title" style="margin:0;"><span></span>Mission Log — Persistent History</div>
                    <div style="font-size:0.78rem;color:var(--muted);">Last 50 requests · survives page refresh</div>
                </div>
                <div class="history-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Query</th>
                                <th>Response</th>
                                <th>Strategy</th>
                                <th>Assigned To</th>
                                <th>Duration</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="history-body">
                            <tr><td colspan="7" style="text-align:center;color:var(--muted);padding:30px;">No queries yet. Send one above!</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- STRATEGY PIE CHART -->
            <div class="card">
                <div class="card-title"><span></span>Strategy Efficiency Comparison</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:30px;align-items:center;">
                    <div style="position:relative;height:260px;">
                        <canvas id="pieChart"></canvas>
                        <div id="pie-center" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;pointer-events:none;">
                            <div style="font-size:1.8rem;font-weight:800;" id="pie-total">0</div>
                            <div style="font-size:0.72rem;color:var(--muted);">Total</div>
                        </div>
                    </div>
                    <div>
                        <p style="font-size:0.82rem;color:var(--muted);margin-bottom:20px;line-height:1.7;">This chart shows how many queries were handled by each routing strategy. Send burst tests with different strategies to see how the distribution changes in real-time!</p>
                        <div id="pie-legend" style="display:flex;flex-direction:column;gap:10px;"></div>
                        <div style="margin-top:20px;padding:12px;border-radius:10px;background:rgba(79,142,255,0.08);border:1px solid rgba(79,142,255,0.2);">
                            <div style="font-size:0.75rem;color:var(--primary);font-weight:700;margin-bottom:6px;">💡 Efficiency Insight</div>
                            <div id="efficiency-tip" style="font-size:0.78rem;color:var(--muted);line-height:1.5;">Run burst tests with each strategy to populate this chart.</div>
                        </div>
                    </div>
                </div>
            </div>
        </main>

        <script>
            // Strategy descriptions
            const stratDesc = {
                least_connections: "⚡ Routes to the agent with the lowest active workload for maximum speed.",
                round_robin: "🔄 Cycles through all agents in order — fair distribution for sequential requests.",
                random: "🎲 Randomly picks an agent — simple but may cause uneven load."
            };
            document.getElementById('strategy').addEventListener('change', e => {
                document.getElementById('strategy-info').textContent = stratDesc[e.target.value];
            });

            // Chart
            const ctx = document.getElementById('distChart').getContext('2d');
            const chart = new Chart(ctx, {
                type: 'bar',
                data: { labels: [], datasets: [{ label: 'Queries Served', data: [], backgroundColor: ['rgba(79,142,255,0.7)','rgba(0,212,255,0.7)','rgba(167,139,250,0.7)'], borderRadius: 8, borderSkipped: false }] },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(79,142,255,0.06)' }, ticks: { color: '#6b82a8', font: { size: 11 } } },
                        x: { grid: { display: false }, ticks: { color: '#6b82a8', font: { size: 11 } } }
                    },
                    plugins: { legend: { display: false } },
                    animation: { duration: 400, easing: 'easeOutQuart' }
                }
            });

            // Pie Chart
            const pieColors = ['#4f8eff','#10d98e','#ff7b3a'];
            const pieLabels = ['Least Connections','Round Robin','Random'];
            const pieKeys = ['least_connections','round_robin','random'];
            const pieCtx = document.getElementById('pieChart').getContext('2d');
            const pieChart = new Chart(pieCtx, {
                type: 'doughnut',
                data: {
                    labels: pieLabels,
                    datasets: [{ data: [0,0,0], backgroundColor: pieColors.map(c=>c+'cc'), borderColor: pieColors, borderWidth: 2, hoverBorderWidth: 3 }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: '65%',
                    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed} requests` } } },
                    animation: { duration: 600, easing: 'easeOutQuart' }
                }
            });

            function updatePieChart(byStrategy) {
                const vals = pieKeys.map(k => byStrategy[k] || 0);
                const total = vals.reduce((a,b)=>a+b,0);
                pieChart.data.datasets[0].data = vals;
                pieChart.update();
                document.getElementById('pie-total').textContent = total;
                const legend = document.getElementById('pie-legend');
                legend.innerHTML = pieKeys.map((k,i) => {
                    const pct = total > 0 ? Math.round(vals[i]/total*100) : 0;
                    return `<div style="display:flex;align-items:center;gap:10px;">
                        <div style="width:12px;height:12px;border-radius:3px;background:${pieColors[i]};flex-shrink:0;"></div>
                        <div style="flex:1;font-size:0.82rem;">${pieLabels[i]}</div>
                        <div style="font-weight:700;color:${pieColors[i]};">${vals[i]} <span style="color:var(--muted);font-weight:400;font-size:0.75rem;">(${pct}%)</span></div>
                    </div>`;
                }).join('');
                // Efficiency tip
                const tip = document.getElementById('efficiency-tip');
                if (total === 0) { tip.textContent = 'Run burst tests with each strategy to populate this chart.'; return; }
                const maxI = vals.indexOf(Math.max(...vals));
                const minI = vals.indexOf(Math.min(...vals));
                const tips = [
                    '⚡ Least Connections is ideal for AI workloads — it avoids overloading busy agents.',
                    '🔄 Round Robin ensures perfectly fair sequential distribution across all agents.',
                    '🎲 Random can cause uneven load — best avoided in production AI deployments.'
                ];
                tip.textContent = `Most used: ${pieLabels[maxI]} (${vals[maxI]} reqs). ${tips[maxI]}`;
            }

            // Escape HTML
            const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

            // Render agents
            function renderAgents(agents) {
                const el = document.getElementById('agents-grid');
                if (!agents.length) { el.innerHTML = '<p style="color:var(--muted);font-size:0.85rem;text-align:center;padding:20px;">No agents registered yet.</p>'; return; }
                el.innerHTML = agents.map((a, i) => {
                    const emojis = ['🤖','🧩','⚙️'];
                    const status = a.is_healthy ? 'healthy' : 'dead';
                    const pulse = a.is_healthy ? '<div class="agent-pulse"></div>' : '';
                    const badge = a.is_healthy ? '<span class="badge badge-ok">ONLINE</span>' : '<span class="badge badge-dead">OFFLINE</span>';
                    const btn = a.is_healthy
                        ? `<button class="agent-btn btn-crash" onclick="control('${a.id}','simulate-crash')">Crash</button>`
                        : `<button class="agent-btn btn-recover" onclick="control('${a.id}','recover')">Recover</button>`;
                    return `
                    <div class="agent-card ${status}">
                        <div class="agent-avatar ${status}">${emojis[i%3]}${pulse}</div>
                        <div class="agent-info">
                            <div class="agent-name">${esc(a.id)}</div>
                            <div class="agent-meta">Serverless Route &nbsp;·&nbsp; ${badge}</div>
                        </div>
                        <div class="agent-stats">
                            <div class="stat-pill">
                                <div class="val" style="color:${a.active_connections>0?'#00d4ff':'#4f8eff'}">${a.active_connections}</div>
                                <div class="lbl">Active</div>
                            </div>
                            <div class="stat-pill">
                                <div class="val">${a.total_handled}</div>
                                <div class="lbl">Total</div>
                            </div>
                        </div>
                        ${btn}
                    </div>`;
                }).join('');
            }

            // Poll status
            async function poll() {
                try {
                    const r = await fetch('/status');
                    const d = await r.json();
                    document.getElementById('m-total').textContent = d.metrics.total_requests;
                    document.getElementById('m-success').textContent = d.metrics.successful;
                    document.getElementById('m-failed').textContent = d.metrics.failed;
                    d.agents.sort((a,b) => a.id.localeCompare(b.id));
                    renderAgents(d.agents);
                    chart.data.labels = d.agents.map(a => a.id.split('(')[0].trim());
                    chart.data.datasets[0].data = d.agents.map(a => a.total_handled);
                    chart.update();
                    updatePieChart(d.metrics.by_strategy || {});
                    const hb = document.getElementById('history-body');
                    if (d.history.length === 0) { hb.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:30px;">No queries yet. Send one above!</td></tr>'; return; }
                    hb.innerHTML = d.history.map(item => `
                        <tr class="${item.success?'row-ok':'row-fail'}">
                            <td style="color:var(--muted);white-space:nowrap;">${item.timestamp}</td>
                            <td>${esc(item.query)}</td>
                            <td><div class="resp-cell">${esc(item.response)}</div></td>
                            <td><code>${item.strategy}</code></td>
                            <td style="font-weight:700;color:var(--cyan);">${esc(item.agent)}</td>
                            <td style="color:var(--purple);">${item.time_taken}s</td>
                            <td>${item.success?'<span style="color:var(--green);font-weight:700;">OK</span>':'<span style="color:var(--red);font-weight:700;">FAIL</span>'}</td>
                        </tr>`).join('');
                } catch(e) { console.error(e); }
            }

            async function control(id, action) {
                await fetch(`/agent-control/${id}/${action}`, { method:'POST' });
                poll();
            }

            async function runBurst() {
                const s = document.getElementById('burst-strategy').value;
                await fetch('/burst', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({strategy:s,count:15}) });
            }

            document.getElementById('q-form').addEventListener('submit', async e => {
                e.preventDefault();
                const q = document.getElementById('q-input').value;
                const s = document.getElementById('strategy').value;
                const btn = document.getElementById('btn-send');
                btn.disabled = true; btn.textContent = '⏳ Processing...';
                document.getElementById('q-input').value = '';
                try {
                    await fetch(`/query?strategy=${s}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({query:q}) });
                } finally {
                    btn.disabled = false; btn.textContent = 'Send to Smart Agent 🚀';
                    poll();
                }
            });

            // Theme toggle
            const savedTheme = localStorage.getItem('sa-theme') || 'dark';
            if (savedTheme === 'light') { document.body.classList.add('light'); document.getElementById('theme-btn').textContent = '☀️ Light Mode'; }
            function toggleTheme() {
                const isLight = document.body.classList.toggle('light');
                const btn = document.getElementById('theme-btn');
                btn.textContent = isLight ? '☀️ Light Mode' : '🌙 Dark Mode';
                localStorage.setItem('sa-theme', isLight ? 'light' : 'dark');
                const gc = isLight ? 'rgba(99,102,241,0.06)' : 'rgba(79,142,255,0.06)';
                const tc = isLight ? '#6b7280' : '#6b82a8';
                chart.options.scales.y.grid.color = gc;
                chart.options.scales.y.ticks.color = tc;
                chart.options.scales.x.ticks.color = tc;
                chart.update();
            }

            setInterval(poll, 1200);
            poll();
        </script>
    </body>
    </html>
    """
    return html
