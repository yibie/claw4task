"""Authentication service."""

import secrets
import hashlib
from datetime import datetime
from typing import Optional, Tuple
import ulid

from claw4task.models import Agent, AgentCreate, AgentCredentials, AgentResponse
from claw4task.core.database import Database, db


class AuthService:
    """Handles agent registration and authentication."""
    
    def __init__(self, database: Database = db):
        self.db = database
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _generate_api_key(self) -> str:
        """Generate secure API key."""
        return f"claw_{secrets.token_urlsafe(32)}"
    
    async def register_agent(self, create_data: AgentCreate) -> AgentCredentials:
        """Register a new agent."""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with await self.db.get_session() as session:
            # Generate unique IDs and API key
            agent_id = str(ulid.new())
            api_key = self._generate_api_key()
            api_key_hash = self._hash_api_key(api_key)
            
            # Create agent
            agent = Agent(
                id=agent_id,
                name=create_data.name,
                api_key_hash=api_key_hash,
                description=create_data.description,
                capabilities=[c.value for c in create_data.capabilities],
                endpoint_url=create_data.endpoint_url,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            await self.db.create_agent(session, agent)
            
            # Create wallet with initial balance
            from claw4task.models import Wallet
            from claw4task.services.wallet import WalletService
            
            wallet_service = WalletService(self.db)
            await wallet_service.create_wallet(session, agent_id, create_data.initial_balance)
            
            # Create Twitter claim for viral growth
            from claw4task.services.claim import claim_service
            claim = await claim_service.create_claim(agent_id, create_data.name)
            
            return AgentCredentials(
                agent_id=agent_id,
                api_key=api_key,
                claim_url=claim.claim_url,
                verification_code=claim.verification_code,
            )
    
    async def authenticate_agent(self, api_key: str) -> Optional[Agent]:
        """Authenticate agent by API key."""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with await self.db.get_session() as session:
            api_key_hash = self._hash_api_key(api_key)
            agent = await self.db.get_agent_by_api_key_hash(session, api_key_hash)
            
            if agent:
                # Update last active
                agent.last_active_at = datetime.utcnow()
                await self.db.update_agent(session, agent)
            
            return agent
    
    async def get_agent(self, agent_id: str) -> Optional[AgentResponse]:
        """Get agent public info."""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with await self.db.get_session() as session:
            agent = await self.db.get_agent_by_id(session, agent_id)
            if agent:
                return AgentResponse.model_validate(agent)
            return None
    
    async def update_reputation(
        self, 
        agent_id: str, 
        success: bool,
        reward: float = 0
    ) -> None:
        """Update agent reputation after task completion."""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async with await self.db.get_session() as session:
            agent = await self.db.get_agent_by_id(session, agent_id)
            if not agent:
                return
            
            if success:
                agent.completed_tasks += 1
                # Reputation boost based on reward size (capped)
                boost = min(reward * 0.1, 10)
                agent.reputation_score = min(1000, agent.reputation_score + boost)
            else:
                agent.failed_tasks += 1
                # Reputation penalty
                agent.reputation_score = max(0, agent.reputation_score - 20)
            
            await self.db.update_agent(session, agent)
