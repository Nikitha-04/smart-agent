# 🧠 Smart Agent — Your Smart Agent

> **Multiple AI agents working simultaneously to solve every problem**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

---

## 📌 Overview

**Smart Agent** is a production-grade **Distributed AI Load Balancer** that routes user queries across multiple AI agent instances simultaneously. It maximises throughput, ensures fault tolerance, and provides a beautiful real-time dashboard to monitor all agent activity.

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
| 🌗 **Dark / Light Theme** | Toggle between premium dark mode and vibrant glassmorphism light mode |
| 🔒 **Secure API Key Handling** | Keys stored in `.env`, never hardcoded |
| 🚀 **Burst Testing** | Fire 15 concurrent queries to stress-test load balancing |

---

## 🏗️ Architecture

```
USER / BROWSER  -->  ROUTER (Port 9000)  -->  Agent 1 (8001)
                                          -->  Agent 2 (8002)
                                          -->  Agent 3 (8003)
```

---

## 🛠️ Tech Stack

**Backend:** Python 3.10+, FastAPI, Uvicorn, HTTPX, python-dotenv, OpenAI SDK

**Frontend:** HTML5, Vanilla CSS (glassmorphism), Vanilla JS, Chart.js, Plus Jakarta Sans

**Concepts:** Microservice Architecture, Process Isolation, Service Discovery, Circuit Breaking

---

## 🚀 Getting Started

```bash
# 1. Clone
git clone https://github.com/Nikitha-04/smart-agent.git
cd smart-agent

# 2. Install
pip install -r requirements.txt

# 3. Create .env with your keys
OPENAI_KEY_1=sk-...
OPENAI_KEY_2=sk-...
OPENAI_KEY_3=sk-...

# 4. Run
python start_system.py
```

Open **http://localhost:9000/dashboard**

---

## 📂 Project Structure

```
smart-agent/
├── agent.py             # Agent service (simulation or real OpenAI)
├── router.py            # Load balancer + real-time dashboard
├── start_system.py      # Launches router + 3 agents
├── test_load_balancer.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 👩‍💻 Author

**NIKITHA** — [@Nikitha-04](https://github.com/Nikitha-04)

> *Exploring emerging technologies | Cybersecurity enthusiast*

---

## 📄 License

MIT License
