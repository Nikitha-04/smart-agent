import subprocess
import time
import sys
import os
import signal
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

processes = []

def start_process(command, env_vars=None):
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    print(f"Starting: {command}")
    p = subprocess.Popen(command, shell=True, env=env)
    processes.append(p)

if __name__ == "__main__":
    try:
        # Start Router on port 9000
        start_process(f"{sys.executable} -m uvicorn router:app --port 9000")

        time.sleep(2)  # Give router a moment to start

        # Start Agents on ports 8001, 8002, 8003
        model_name = "GPT-3.5 Turbo"

        key1 = os.getenv("OPENAI_KEY_1", "")
        key2 = os.getenv("OPENAI_KEY_2", "")
        key3 = os.getenv("OPENAI_KEY_3", "")

        start_process(f"{sys.executable} -m uvicorn agent:app --port 8001", {"PORT": "8001", "MODEL_NAME": model_name, "INSTANCE_NUM": "1", "OPENAI_API_KEY": key1})
        start_process(f"{sys.executable} -m uvicorn agent:app --port 8002", {"PORT": "8002", "MODEL_NAME": model_name, "INSTANCE_NUM": "2", "OPENAI_API_KEY": key2})
        start_process(f"{sys.executable} -m uvicorn agent:app --port 8003", {"PORT": "8003", "MODEL_NAME": model_name, "INSTANCE_NUM": "3", "OPENAI_API_KEY": key3})

        print("\n==============================================")
        print("\U0001f680 System Started Successfully")
        print("\U0001f4ca Router Dashboard: http://localhost:9000/dashboard")
        print("\U0001f4e8 Send Queries to: POST http://localhost:9000/query")
        print("   (Use test_load_balancer.py to send traffic)")
        print("\U0001f6d1 Press Ctrl+C to stop all processes.")
        print("==============================================\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down processes...")
        for p in processes:
            p.terminate()
        sys.exit(0)
