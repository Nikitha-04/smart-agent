# Smart Agent — Nasiko / Antigravity Configuration

## Project Overview
Smart Agent is a distributed AI load balancer built with FastAPI. It spawns multiple AI agent processes and routes queries across them using configurable strategies.

## Entry Point
```
python start_system.py
```

## How It Works
1. `start_system.py` launches the router on port 9000 and 3 agents on ports 8001-8003
2. Agents self-register to the router via heartbeat pings every 2 seconds
3. The router distributes incoming queries using the selected strategy
4. The dashboard at `/dashboard` shows real-time metrics

## Routing Strategies
- `round_robin` — cycles through all agents in order
- `least_connections` — picks the least busy agent
- `random` — randomly selects an agent

## API Endpoints
- `GET /dashboard` — real-time web dashboard
- `POST /query?strategy=round_robin` — send a query
- `POST /burst` — fire 15 concurrent test queries
- `GET /status` — get JSON metrics and agent health
- `POST /heartbeat` — agent registration (internal)

## Environment Variables
```
OPENAI_KEY_1=sk-...
OPENAI_KEY_2=sk-...
OPENAI_KEY_3=sk-...
```

## Dependencies
See `requirements.txt`. Install with: `pip install -r requirements.txt`
