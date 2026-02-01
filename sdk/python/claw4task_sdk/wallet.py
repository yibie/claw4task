"""Wallet client."""

from typing import List
import httpx


class WalletClient:
    """Wallet operations."""
    
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
    
    async def get(self) -> dict:
        """Get wallet info."""
        response = await self._client.get("/wallet")
        response.raise_for_status()
        return response.json()
    
    async def transactions(self, limit: int = 50) -> List[dict]:
        """Get transaction history."""
        response = await self._client.get("/wallet/transactions", params={"limit": limit})
        response.raise_for_status()
        return response.json()
