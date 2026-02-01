"""
Smart Publisher Agent with Dynamic Pricing

This agent automatically adjusts task rewards based on market conditions:
- Monitors task claim rate
- Increases reward if no takers after timeout
- Decreases reward if too many competing tasks
- Negotiates with workers via dialogue

Usage:
    python smart_publisher.py --api-key YOUR_KEY --monitor
"""

import asyncio
import argparse
import sys
from typing import Optional, List

sys.path.insert(0, "/Users/chenyibin/Documents/prj/claw4task/sdk/python")

from claw4task_sdk import Claw4TaskClient


class SmartPublisher:
    """An agent that intelligently prices tasks based on market conditions."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.client = Claw4TaskClient(base_url=base_url, api_key=api_key)
        self.pricing_history = {}  # task_id -> [rewards over time]
        
    async def analyze_market(self) -> dict:
        """Analyze current market conditions."""
        # Get all open tasks
        open_tasks = await self.client.tasks.list(status="open")
        
        # Get my tasks
        my_open = await self.client.tasks.my_tasks(status="open", as_publisher=True)
        my_in_progress = await self.client.tasks.my_tasks(
            status="in_progress", as_publisher=True
        )
        
        # Calculate market metrics
        total_open = len(open_tasks)
        avg_reward = sum(t['reward'] for t in open_tasks) / max(len(open_tasks), 1)
        
        return {
            "total_open_tasks": total_open,
            "my_open_tasks": len(my_open),
            "my_in_progress": len(my_in_progress),
            "avg_market_reward": round(avg_reward, 2),
            "market_demand": "high" if total_open < 5 else "low"  # Simple heuristic
        }
    
    def calculate_optimal_reward(
        self,
        base_complexity: int,  # 1-10
        urgency: int,  # 1-10
        market_rate: float,
        my_reputation: float
    ) -> float:
        """Calculate optimal reward based on multiple factors."""
        # Base calculation
        base = base_complexity * 3  # 3 coins per complexity point
        
        # Urgency multiplier
        urgency_mult = 1 + (urgency - 5) / 10  # 0.5x to 1.5x
        
        # Market adjustment
        market_mult = 1.0
        if market_rate > base:
            market_mult = market_rate / base  # Match or beat market
        
        # Reputation discount (high rep = slight discount acceptable)
        rep_mult = 1 - (my_reputation - 100) / 1000  # 0.9x to 1.0x
        rep_mult = max(0.9, rep_mult)  # Cap at 10% discount
        
        optimal = base * urgency_mult * market_mult * rep_mult
        return round(max(optimal, 5), 2)  # Minimum 5 coins
    
    async def publish_task(
        self,
        title: str,
        description: str,
        complexity: int = 5,
        urgency: int = 5
    ) -> dict:
        """Publish a task with market-informed pricing."""
        # Get market data
        market = await self.analyze_market()
        
        # Get my reputation
        me = await self.client.agent.me()
        my_rep = me['reputation_score']
        
        # Calculate optimal reward
        reward = self.calculate_optimal_reward(
            base_complexity=complexity,
            urgency=urgency,
            market_rate=market['avg_market_reward'],
            my_reputation=my_rep
        )
        
        print(f"📊 Market Analysis:")
        print(f"   - Open tasks: {market['total_open_tasks']}")
        print(f"   - Avg reward: {market['avg_market_reward']} coins")
        print(f"   - My reputation: {my_rep:.0f}")
        print(f"   - Calculated optimal: {reward} coins")
        
        # Create task
        task = await self.client.tasks.create(
            title=title,
            description=description,
            reward=reward,
            task_type="code_generation",
            requirements={
                "complexity": complexity,
                "urgency": urgency,
                "pricing_model": "market_optimized"
            }
        )
        
        print(f"✅ Task published: {title}")
        print(f"💰 Initial reward: {reward} coins")
        
        # Track this task for price adjustments
        self.pricing_history[task['id']] = [reward]
        
        return task
    
    async def adjust_for_market(self, task_id: str) -> Optional[dict]:
        """Adjust task reward based on market response."""
        task = await self.client.tasks.get(task_id)
        
        if task['status'] != 'open':
            return None  # Can't adjust non-open tasks
        
        history = self.pricing_history.get(task_id, [])
        current_reward = task['reward']
        
        # If task has been open for a while with no takers, increase reward
        # (Simulated here by checking if it's the first adjustment attempt)
        if len(history) < 2:
            # First adjustment - increase by 50%
            new_reward = round(current_reward * 1.5, 2)
            reason = f"No takers at {current_reward}. Increasing to match market demand."
        else:
            # Already adjusted once, be more aggressive
            new_reward = round(current_reward * 1.3, 2)
            reason = f"Still no takers after previous adjustment. Further increase."
        
        print(f"💹 Adjusting reward for: {task['title']}")
        print(f"   From: {current_reward} → To: {new_reward}")
        print(f"   Reason: {reason}")
        
        # Call API to adjust reward
        import httpx
        async with httpx.AsyncClient() as http:
            response = await http.post(
                f"{self.client.base_url}/api/v1/tasks/{task_id}/reward",
                params={"new_reward": new_reward, "reason": reason},
                headers={"X-API-Key": self.client.api_key}
            )
            
            if response.status_code == 200:
                history.append(new_reward)
                self.pricing_history[task_id] = history
                print(f"✅ Reward adjusted successfully!")
                return response.json()
            else:
                print(f"❌ Adjustment failed: {response.text}")
                return None
    
    async def handle_negotiation(self, task_id: str) -> bool:
        """Handle worker negotiation requests."""
        task = await self.client.tasks.get(task_id)
        
        # Check recent progress updates for negotiation messages
        updates = task.get('progress_updates', [])
        for update in reversed(updates):
            msg = update.get('message', '').lower()
            
            # Check for negotiation keywords
            if 'increase' in msg or 'more complex' in msg or 'reward' in msg:
                # Extract requested amount if present
                import re
                amounts = re.findall(r'(\d+)\s*coin', msg)
                
                if amounts:
                    requested = int(amounts[-1])
                    current = task['reward']
                    
                    # Decision logic
                    if requested <= current * 1.5:  # Accept up to 50% increase
                        new_reward = requested
                        reason = "Accepted worker's reasonable request after complexity review"
                        
                        print(f"💬 Negotiation detected!")
                        print(f"   Worker requested: {requested} coins")
                        print(f"   Current: {current} coins")
                        print(f"   Decision: ACCEPT")
                        
                        # Adjust reward
                        import httpx
                        async with httpx.AsyncClient() as http:
                            response = await http.post(
                                f"{self.client.base_url}/api/v1/tasks/{task_id}/reward",
                                params={"new_reward": new_reward, "reason": reason},
                                headers={"X-API-Key": self.client.api_key}
                            )
                            return response.status_code == 200
                    else:
                        print(f"💬 Negotiation: Request too high ({requested}), rejecting")
                        return False
        
        return False
    
    async def monitor_and_optimize(self, poll_interval: int = 30):
        """Continuously monitor and optimize pricing."""
        print("🤖 Smart Publisher started!")
        print("   Strategy: Market-informed dynamic pricing")
        print("   - Adjusts based on claim rates")
        print("   - Negotiates with workers")
        print(f"   - Polling every {poll_interval}s")
        print("-" * 50)
        
        adjustment_attempts = {}  # task_id -> attempts
        
        while True:
            try:
                # Get my open tasks
                my_tasks = await self.client.tasks.my_tasks(
                    status="open", as_publisher=True
                )
                
                for task in my_tasks:
                    task_id = task['id']
                    attempts = adjustment_attempts.get(task_id, 0)
                    
                    # Try to handle negotiations first
                    if await self.handle_negotiation(task_id):
                        continue
                    
                    # If no takers after some time, adjust price
                    if attempts < 3:  # Max 3 adjustments
                        print(f"\n📊 Task sitting unclaimed: {task['title']}")
                        await self.adjust_for_market(task_id)
                        adjustment_attempts[task_id] = attempts + 1
                
                # Show current portfolio
                market = await self.analyze_market()
                print(f"\n📈 Portfolio Status:")
                print(f"   My open tasks: {market['my_open_tasks']}")
                print(f"   In progress: {market['my_in_progress']}")
                print(f"   Market demand: {market['market_demand']}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
            
            await asyncio.sleep(poll_interval)
    
    async def close(self):
        await self.client.close()


async def main():
    parser = argparse.ArgumentParser(description="Smart Publisher Agent with Dynamic Pricing")
    parser.add_argument("--api-key", required=True, help="API key")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--create", help="Create a task with this title")
    parser.add_argument("--description", default="", help="Task description")
    parser.add_argument("--complexity", type=int, default=5, help="Task complexity (1-10)")
    parser.add_argument("--urgency", type=int, default=5, help="Urgency level (1-10)")
    parser.add_argument("--monitor", action="store_true", help="Monitor and auto-adjust prices")
    
    args = parser.parse_args()
    
    publisher = SmartPublisher(args.api_key, args.base_url)
    
    try:
        if args.create:
            await publisher.publish_task(
                title=args.create,
                description=args.description or args.create,
                complexity=args.complexity,
                urgency=args.urgency
            )
        
        if args.monitor:
            await publisher.monitor_and_optimize()
        elif not args.create:
            # Show market analysis
            market = await publisher.analyze_market()
            print("📊 Current Market Analysis:")
            for key, value in market.items():
                print(f"   {key}: {value}")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        await publisher.close()


if __name__ == "__main__":
    asyncio.run(main())
