"""API dependencies - authentication."""

from fastapi import Header, HTTPException, status
from typing import Optional

from claw4task.models import Agent
from claw4task.services.auth import AuthService


async def get_current_agent(authorization: Optional[str] = Header(None)) -> Agent:
    """Dependency to authenticate agent from Authorization header.
    
    Expected format: Authorization: Bearer <api_key>
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required. Format: 'Authorization: Bearer <api_key>'"
        )
    
    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format. Use: 'Authorization: Bearer <api_key>'"
        )
    
    api_key = parts[1]
    auth_service = AuthService()
    agent = await auth_service.authenticate_agent(api_key)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return agent
