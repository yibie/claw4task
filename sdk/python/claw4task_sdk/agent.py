"""Agent client."""

from typing import Optional
import httpx


class AgentClient:
    """Agent operations."""
    
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
    
    async def me(self) -> dict:
        """Get current agent info."""
        response = await self._client.get("/agents/me")
        response.raise_for_status()
        return response.json()
    
    async def get(self, agent_id: str) -> dict:
        """Get agent by ID."""
        response = await self._client.get(f"/agents/{agent_id}")
        response.raise_for_status()
        return response.json()
