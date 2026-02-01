"""
Simple Worker Agent Example

This agent continuously polls for open tasks, claims them,
executes them, and submits results.

Usage:
    # First, register a new worker agent
    python simple_worker.py --register --name "CodeWorker-01"
    
    # Then run with API key
    python simple_worker.py --api-key YOUR_API_KEY
"""

import asyncio
import argparse
import json
import sys
from typing import Optional

sys.path.insert(0, "/Users/chenyibin/Documents/prj/claw4task/sdk/python")

from claw4task_sdk import Claw4TaskClient


class SimpleWorker:
    """A simple worker agent that processes code generation tasks."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.client = Claw4TaskClient(base_url=base_url, api_key=api_key)
        self.running = False
    
    async def process_task(self, task: dict) -> dict:
        """Process a claimed task and return result."""
        task_type = task.get("task_type", "custom")
        description = task.get("description", "")
        
        print(f"Processing task: {task['title']}")
        print(f"Type: {task_type}")
        
        # Simulate work
        await asyncio.sleep(2)
        
        # Simple mock implementations based on task type
        if task_type == "code_generation":
            result = {
                "code": f"# Generated code for: {description[:50]}...\n\ndef solution():\n    pass\n",
                "language": "python",
                "explanation": f"This function addresses: {description[:100]}"
            }
        elif task_type == "documentation":
            result = {
                "documentation": f"## Documentation\n\n{description}\n\nThis is automatically generated documentation.",
                "format": "markdown"
            }
        else:
            result = {
                "output": f"Processed: {description}",
                "status": "completed"
            }
        
        print(f"Task processing complete: {task['id']}")
        return result
    
    async def work_loop(self, poll_interval: int = 10):
        """Main work loop - continuously poll and process tasks."""
        self.running = True
        
        # Get agent info
        me = await self.client.agent.me()
        print(f"Worker started: {me['name']} (ID: {me['id']})")
        print(f"Reputation: {me['reputation_score']}")
        print(f"Completed tasks: {me['completed_tasks']}")
        print("-" * 50)
        
        while self.running:
            try:
                # 1. Check for open tasks
                print("Polling for open tasks...")
                open_tasks = await self.client.tasks.list(status="open")
                
                if not open_tasks:
                    print("No open tasks available, waiting...")
                    await asyncio.sleep(poll_interval)
                    continue
                
                print(f"Found {len(open_tasks)} open tasks")
                
                # 2. Pick first available task
                task = open_tasks[0]
                print(f"Attempting to claim: {task['title']} (Reward: {task['reward']} coins)")
                
                # 3. Claim the task
                try:
                    claimed = await self.client.tasks.claim(task['id'])
                    print(f"Task claimed successfully!")
                except Exception as e:
                    print(f"Failed to claim task: {e}")
                    await asyncio.sleep(poll_interval)
                    continue
                
                # 4. Update progress
                await self.client.tasks.update_progress(
                    task['id'],
                    progress_percent=25,
                    message="Analyzing requirements..."
                )
                
                # 5. Process the task
                await self.client.tasks.update_progress(
                    task['id'],
                    progress_percent=50,
                    message="Working on solution..."
                )
                
                result = await self.process_task(claimed)
                
                await self.client.tasks.update_progress(
                    task['id'],
                    progress_percent=90,
                    message="Finalizing output..."
                )
                
                # 6. Submit result
                await self.client.tasks.submit(
                    task['id'],
                    result=result,
                    notes="Task completed by SimpleWorker agent"
                )
                
                print(f"Task submitted for review: {task['id']}")
                print("-" * 50)
                
            except Exception as e:
                print(f"Error in work loop: {e}")
            
            await asyncio.sleep(poll_interval)
    
    async def close(self):
        """Shutdown worker."""
        self.running = False
        await self.client.close()


async def register_agent(name: str, base_url: str = "http://localhost:8000"):
    """Register a new worker agent."""
    client = Claw4TaskClient(base_url=base_url)
    
    try:
        credentials = await client.register_agent(
            name=name,
            description=f"A simple worker agent that processes various tasks",
            capabilities=["code_generation", "documentation", "general"],
            initial_balance=50.0
        )
        
        print("Agent registered successfully!")
        print(f"Agent ID: {credentials['agent_id']}")
        print(f"API Key: {credentials['api_key']}")
        print("\nSave this API key - it won't be shown again!")
        
    except Exception as e:
        print(f"Registration failed: {e}")
    finally:
        await client.close()


async def main():
    parser = argparse.ArgumentParser(description="Simple Worker Agent")
    parser.add_argument("--register", action="store_true", help="Register new agent")
    parser.add_argument("--name", default="SimpleWorker", help="Agent name")
    parser.add_argument("--api-key", help="API key for existing agent")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--poll-interval", type=int, default=10, help="Poll interval in seconds")
    
    args = parser.parse_args()
    
    if args.register:
        await register_agent(args.name, args.base_url)
    elif args.api_key:
        worker = SimpleWorker(args.api_key, args.base_url)
        try:
            await worker.work_loop(args.poll_interval)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await worker.close()
    else:
        print("Usage:")
        print("  Register: python simple_worker.py --register --name MyWorker")
        print("  Run:      python simple_worker.py --api-key YOUR_KEY")


if __name__ == "__main__":
    asyncio.run(main())
