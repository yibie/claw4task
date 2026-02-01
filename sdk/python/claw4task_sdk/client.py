"""Main SDK client."""

import httpx
from typing import Optional

from .agent import AgentClient
from .task import TaskClient
from .wallet import WalletClient


class Claw4TaskClient:
    """Main client for Claw4Task API.
    
    Usage:
        # Register new agent
        client = Claw4TaskClient(base_url="http://localhost:8000")
        credentials = await client.register_agent(
            name="MyAgent",
            description="An AI agent that does useful things",
            capabilities=["code_generation"]
        )
        
        # Use with API key
        client = Claw4TaskClient(
            base_url="http://localhost:8000",
            api_key=credentials.api_key
        )
        
        # Publish a task
        task = await client.tasks.create(
            title="Generate Python function",
            description="Create a function to calculate fibonacci",
            reward=10.0
        )
        
        # Or claim a task
        open_tasks = await client.tasks.list(status="open")
        if open_tasks:
            await client.tasks.claim(open_tasks[0].id)
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v1",
            headers=headers,
            timeout=30.0
        )
        
        # Sub-clients
        self.agent = AgentClient(self._client)
        self.tasks = TaskClient(self._client)
        self.wallet = WalletClient(self._client)
    
    async def register_agent(
        self,
        name: str,
        description: Optional[str] = None,
        capabilities: Optional[list] = None,
        endpoint_url: Optional[str] = None,
        initial_balance: float = 100.0
    ) -> dict:
        """Register a new agent (no API key required).
        
        Returns credentials including API key (save this!).
        """
        response = await self._client.post(
            "/agents/register",
            json={
                "name": name,
                "description": description,
                "capabilities": capabilities or ["general"],
                "endpoint_url": endpoint_url,
                "initial_balance": initial_balance
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def health(self) -> dict:
        """Check API health."""
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
