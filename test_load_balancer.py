import asyncio
import httpx
import time
import argparse

async def send_query(client, index, strategy):
    try:
        start_time = time.time()
        response = await client.post(
            "http://localhost:9000/query", 
            params={"strategy": strategy},
            json={"query": f"Task {index}"},
            timeout=20.0
        )
        elapsed = time.time() - start_time
        data = response.json()
        print(f"✅ Task {index:02d} routed to {data.get('agent_id')} (Took {elapsed:.2f}s, Delay was {data.get('delay'):.2f}s)")
    except Exception as e:
        print(f"❌ Task {index:02d} failed: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Test the AI Agent Load Balancer")
    parser.add_argument("--strategy", type=str, default="least_connections", choices=["least_connections", "round_robin", "random"], help="Routing strategy to use")
    parser.add_argument("--count", type=int, default=15, help="Number of concurrent requests to send")
    args = parser.parse_args()
    
    print(f"🚀 Sending {args.count} concurrent requests using strategy: '{args.strategy}'...")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        tasks = [send_query(client, i, args.strategy) for i in range(args.count)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
