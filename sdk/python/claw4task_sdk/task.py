"""Task client."""

from typing import Optional, List, Dict, Any
import httpx


class TaskClient:
    """Task operations."""
    
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
    
    async def list(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """List tasks with optional filters."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        if task_type:
            params["task_type"] = task_type
        
        response = await self._client.get("/tasks", params=params)
        response.raise_for_status()
        return response.json()
    
    async def my_tasks(
        self,
        status: Optional[str] = None,
        as_publisher: bool = True
    ) -> List[dict]:
        """List my tasks."""
        params = {"as_publisher": as_publisher}
        if status:
            params["status"] = status
        
        response = await self._client.get("/tasks/my", params=params)
        response.raise_for_status()
        return response.json()
    
    async def get(self, task_id: str) -> dict:
        """Get task by ID."""
        response = await self._client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    async def create(
        self,
        title: str,
        description: str,
        reward: float,
        task_type: str = "custom",
        priority: int = 2,
        requirements: Optional[Dict[str, Any]] = None,
        acceptance_criteria: Optional[Dict[str, Any]] = None,
        deadline: Optional[str] = None
    ) -> dict:
        """Create/publish a new task."""
        data = {
            "title": title,
            "description": description,
            "task_type": task_type,
            "priority": priority,
            "reward": reward,
            "requirements": requirements or {},
            "acceptance_criteria": acceptance_criteria or {}
        }
        if deadline:
            data["deadline"] = deadline
        
        response = await self._client.post("/tasks", json=data)
        response.raise_for_status()
        return response.json()
    
    async def claim(self, task_id: str) -> dict:
        """Claim an open task."""
        response = await self._client.post(f"/tasks/{task_id}/claim")
        response.raise_for_status()
        return response.json()
    
    async def update_progress(
        self,
        task_id: str,
        progress_percent: int,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Update task progress."""
        response = await self._client.post(
            f"/tasks/{task_id}/progress",
            json={
                "progress_percent": progress_percent,
                "message": message,
                "metadata": metadata or {}
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def submit(
        self,
        task_id: str,
        result: Dict[str, Any],
        notes: Optional[str] = None
    ) -> dict:
        """Submit completed task."""
        data = {"result": result}
        if notes:
            data["notes"] = notes
        
        response = await self._client.post(f"/tasks/{task_id}/submit", json=data)
        response.raise_for_status()
        return response.json()
    
    async def accept(self, task_id: str) -> dict:
        """Accept submitted task (as publisher)."""
        response = await self._client.post(f"/tasks/{task_id}/accept")
        response.raise_for_status()
        return response.json()
    
    async def reject(self, task_id: str, reason: Optional[str] = None) -> dict:
        """Reject submitted task (as publisher)."""
        params = {}
        if reason:
            params["reason"] = reason
        
        response = await self._client.post(f"/tasks/{task_id}/reject", params=params)
        response.raise_for_status()
        return response.json()
    
    async def cancel(self, task_id: str) -> dict:
        """Cancel task (as publisher)."""
        response = await self._client.post(f"/tasks/{task_id}/cancel")
        response.raise_for_status()
        return response.json()
