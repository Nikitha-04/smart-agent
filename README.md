# 🧠 Smart Agent — Your Smart Agent

> **Multiple AI agents working simultaneously to solve every problem**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

---

## 📌 Overview

**Smart Agent** is a production-grade **Distributed AI Load Balancer** that routes user queries across multiple AI agent instances simultaneously. It maximises throughput, ensures fault tolerance, and provides a beautiful real-time dashboard to monitor all agent activity.

This project solves a core problem in AI infrastructure:
> *"How do we handle thousands of concurrent AI queries without bottlenecks, crashes, or slow responses?"*

The answer: **Distribute the load intelligently across multiple agents.**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔄 **Round Robin** | Cycles queries evenly across all agents in order |
| ⚡ **Least Connections** | Routes to the agent with the lowest active workload |
| 🎲 **Random** | Randomly selects an agent for each query |
| 💓 **Heartbeat Monitoring** | Agents ping the router every 2s; dead agents are removed instantly |
| 🔌 **Circuit Breaking** | Unhealthy agents are bypassed automatically |
| 📊 **Real-Time Dashboard** | Live metrics, bar chart, and strategy comparison pie chart |
| 🌗 **Dark / Light Theme** | Toggle between a premium dark mode and vibrant glassmorphism light mode |
| 🔒 **Secure API Key Handling** | Keys stored in `.env`, never hardcoded |
| 🚀 **Burst Testing** | Fire 15 concurrent queries to stress-test load balancing |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   USER / BROWSER                    │
│              http://localhost:9000/dashboard         │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              SMART AGENT ROUTER  (Port 9000)        │
│   • Receives all queries                            │
│   • Selects best agent via chosen strategy          │
│   • Tracks metrics, history, and health             │
└──────┬─────────────────┬──────────────────┬─────────┘
       │                 │                  │
       ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Agent 1     │  │  Agent 2     │  │  Agent 3     │
│  Port 8001   │  │  Port 8002   │  │  Port 8003   │
│  🤖 GPT-3.5  │  │  🧩 GPT-3.5  │  │  ⚙️ GPT-3.5  │
│  Key 1       │  │  Key 2       │  │  Key 3       │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core language with async/await concurrency |
| **FastAPI** | High-performance async web framework for Router & Agents |
| **Uvicorn** | ASGI server to run all 4 processes concurrently |
| **HTTPX** | Async HTTP client for heartbeats and request forwarding |
| **python-dotenv** | Secure environment variable loading |
| **OpenAI SDK** | AsyncOpenAI client for real GPT-3.5/4 integration |

### Frontend (built into FastAPI)
| Technology | Purpose |
|---|---|
| **HTML5 + Vanilla CSS** | Premium dashboard UI with glassmorphism and dark/light themes |
| **Vanilla JavaScript (ES6+)** | Real-time polling, dynamic rendering, theme toggle |
| **Chart.js** | Bar chart (load distribution) + Doughnut chart (strategy comparison) |
| **Plus Jakarta Sans** | Google Fonts — modern premium typography |

### Key Concepts Applied
- **Microservice Architecture** — Router and each Agent are independent processes
- **Process Isolation** — `subprocess` bypasses Python's GIL for true parallelism
- **Service Discovery** — Agents auto-register via heartbeat pings
- **Circuit Breaking** — Dead agents removed from routing pool instantly

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- pip

### 1. Clone the repository
```bash
git clone https://github.com/Nikitha-04/smart-agent.git
cd smart-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
Create a `.env` file in the root directory:
```env
OPENAI_KEY_1=sk-your-first-api-key-here
OPENAI_KEY_2=sk-your-second-api-key-here
OPENAI_KEY_3=sk-your-third-api-key-here
```
> ⚠️ **Never commit your `.env` file.** It is listed in `.gitignore`.

### 4. Start the system
```bash
python start_system.py
```

### 5. Open the dashboard
Visit: **[http://localhost:9000/dashboard](http://localhost:9000/dashboard)**

---

## 📂 Project Structure

```
smart-agent/
├── agent.py            # Agent service — handles queries (simulation or real OpenAI)
├── router.py           # Load balancer router + real-time dashboard HTML
├── start_system.py     # Orchestrator — launches router + 3 agents as subprocesses
├── test_load_balancer.py # Test script for validating load balancing
├── requirements.txt    # Python dependencies
├── .env                # 🔒 Secret API keys (NOT committed to git)
├── .gitignore          # Protects sensitive files
└── README.md           # This file
```

---

## 📊 Dashboard Features

### Real-Time Panels
- **Active Agent Pool** — Shows each agent's health status, active tasks, and total queries served
- **Load Distribution Chart** — Bar chart updating every 1.2s showing workload per agent
- **Mission Control** — Send queries and choose routing strategy
- **🔥 Burst Test** — Fire 15 simultaneous queries to demonstrate load balancing

### Strategy Comparison Pie Chart
After running burst tests with different strategies, the pie chart at the bottom shows:
- How many queries each strategy handled
- Percentage split between strategies
- 💡 **Efficiency Insight** — which strategy is most efficient and why

---

## 🧪 Testing

Run the included test script to validate the load balancer:
```bash
python test_load_balancer.py
```

---

## 🔮 Future Improvements

- [ ] **Dynamic Scaling** — Add/remove agents at runtime without restart
- [ ] **Persistence Layer** — SQLite/Redis for metrics across reboots  
- [ ] **Auth Layer** — JWT-based dashboard authentication
- [ ] **Docker Support** — Containerise each agent independently
- [ ] **Kubernetes Ready** — Helm chart for production deployment

---

## 👩‍💻 Author

**NIKITHA** — [@Nikitha-04](https://github.com/Nikitha-04)

> *Exploring emerging technologies | Cybersecurity enthusiast*

---

## 📄 License

This project is licensed under the MIT License.
