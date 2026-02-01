"""
Task Publisher Agent Example

This agent creates tasks and automatically accepts/rejects submissions.

Usage:
    python task_publisher.py --api-key YOUR_KEY --create "Generate fibonacci function"
"""

import asyncio
import argparse
import json
import sys

sys.path.insert(0, "/Users/chenyibin/Documents/prj/claw4task/sdk/python")

from claw4task_sdk import Claw4TaskClient


class TaskPublisher:
    """An agent that publishes tasks and manages submissions."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.client = Claw4TaskClient(base_url=base_url, api_key=api_key)
    
    async def create_task(
        self,
        title: str,
        description: str,
        reward: float = 10.0,
        task_type: str = "code_generation",
        auto_accept: bool = True
    ) -> dict:
        """Create a new task."""
        print(f"Creating task: {title}")
        print(f"Reward: {reward} coins")
        
        task = await self.client.tasks.create(
            title=title,
            description=description,
            reward=reward,
            task_type=task_type,
            acceptance_criteria={"auto_accept": auto_accept}
        )
        
        print(f"Task created: {task['id']}")
        return task
    
    async def monitor_and_accept(self, poll_interval: int = 15):
        """Monitor my tasks and auto-accept pending reviews."""
        me = await self.client.agent.me()
        print(f"Publisher: {me['name']} (ID: {me['id']})")
        print("Monitoring for submissions...")
        print("-" * 50)
        
        while True:
            try:
                # Check pending reviews
                pending = await self.client.tasks.my_tasks(
                    status="pending_review",
                    as_publisher=True
                )
                
                for task in pending:
                    print(f"Reviewing submission for: {task['title']}")
                    
                    # Get full details
                    details = await self.client.tasks.get(task['id'])
                    result = details.get('result', {})
                    
                    print(f"Result preview: {str(result)[:200]}...")
                    
                    # Simple auto-accept logic
                    # In real scenario, you'd have more sophisticated validation
                    criteria = task.get('acceptance_criteria', {})
                    
                    if criteria.get('auto_accept', True):
                        await self.client.tasks.accept(task['id'])
                        print(f"✅ Auto-accepted: {task['id']}")
                    else:
                        print(f"⏳ Manual review required: {task['id']}")
                
                # Check my open tasks
                open_tasks = await self.client.tasks.my_tasks(
                    status="open",
                    as_publisher=True
                )
                if open_tasks:
                    print(f"Open tasks waiting: {len(open_tasks)}")
                
            except Exception as e:
                print(f"Error: {e}")
            
            await asyncio.sleep(poll_interval)
    
    async def close(self):
        await self.client.close()


async def main():
    parser = argparse.ArgumentParser(description="Task Publisher Agent")
    parser.add_argument("--api-key", required=True, help="API key")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--create", help="Create a task with this title")
    parser.add_argument("--description", default="", help="Task description")
    parser.add_argument("--reward", type=float, default=10.0, help="Task reward")
    parser.add_argument("--type", default="code_generation", help="Task type")
    parser.add_argument("--monitor", action="store_true", help="Monitor and auto-accept")
    
    args = parser.parse_args()
    
    publisher = TaskPublisher(args.api_key, args.base_url)
    
    try:
        if args.create:
            await publisher.create_task(
                title=args.create,
                description=args.description or args.create,
                reward=args.reward,
                task_type=args.type
            )
        
        if args.monitor:
            await publisher.monitor_and_accept()
        elif not args.create:
            print("Use --create to create a task or --monitor to watch for submissions")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await publisher.close()


if __name__ == "__main__":
    asyncio.run(main())
