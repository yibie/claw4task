"""Twitter claim verification service for viral growth."""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from claw4task.models.claim import AgentClaim, ClaimStatusResponse
from claw4task.core.database import db, AgentDB


class ClaimService:
    """Handles Twitter claim verification."""
    
    # In-memory store for claims (use Redis in production)
    _claims: dict = {}  # claim_token -> AgentClaim
    _agent_claims: dict = {}  # agent_id -> claim_token
    
    def generate_claim_token(self, agent_id: str) -> str:
        """Generate unique claim token."""
        # Create token based on agent_id + random
        random_part = secrets.token_urlsafe(16)
        token_input = f"{agent_id}:{random_part}:{datetime.utcnow().isoformat()}"
        token_hash = hashlib.sha256(token_input.encode()).hexdigest()[:24]
        return f"claw4task_claim_{token_hash}"
    
    def generate_verification_code(self) -> str:
        """Generate short verification code for tweet."""
        # Format: word-XXXX (e.g., "lobster-A3F9")
        words = ["lobster", "crab", "shrimp", "krill", "prawn", "crayfish"]
        word = secrets.choice(words)
        code = secrets.token_hex(2).upper()[:4]
        return f"{word}-{code}"
    
    async def create_claim(self, agent_id: str, agent_name: str) -> AgentClaim:
        """Create new claim for agent registration."""
        # Check if already has pending claim
        if agent_id in self._agent_claims:
            old_token = self._agent_claims[agent_id]
            if old_token in self._claims:
                old_claim = self._claims[old_token]
                if old_claim.status == "pending" and old_claim.expires_at > datetime.utcnow():
                    return old_claim  # Return existing valid claim
        
        # Create new claim
        claim_token = self.generate_claim_token(agent_id)
        verification_code = self.generate_verification_code()
        
        claim = AgentClaim(
            agent_id=agent_id,
            claim_token=claim_token,
            claim_url=f"https://claw4task.fly.dev/claim/{claim_token}",
            verification_code=verification_code,
            status="pending",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        
        # Store claim
        self._claims[claim_token] = claim
        self._agent_claims[agent_id] = claim_token
        
        return claim
    
    async def get_claim_status(self, agent_id: str) -> ClaimStatusResponse:
        """Get claim status for an agent."""
        if agent_id not in self._agent_claims:
            return ClaimStatusResponse(
                status="not_started",
                message="No claim initiated. Register your agent first.",
                claim_url=None,
                verification_code=None
            )
        
        token = self._agent_claims[agent_id]
        if token not in self._claims:
            return ClaimStatusResponse(
                status="not_found",
                message="Claim not found. Please register again.",
                claim_url=None,
                verification_code=None
            )
        
        claim = self._claims[token]
        
        # Check expiration
        if claim.status == "pending" and claim.expires_at < datetime.utcnow():
            claim.status = "expired"
        
        # Build response
        response_data = {
            "status": claim.status,
            "claim_url": claim.claim_url if claim.status == "pending" else None,
            "verification_code": claim.verification_code if claim.status == "pending" else None,
            "twitter_handle": claim.twitter_handle,
            "claimed_at": claim.claimed_at,
        }
        
        # Add appropriate message
        if claim.status == "pending":
            response_data["message"] = "⏳ Waiting for Twitter verification"
            response_data["tweet_template"] = self._generate_tweet_template(
                claim.verification_code, 
                claim.claim_url
            )
        elif claim.status == "claimed":
            response_data["message"] = f"✅ Verified! Twitter: @{claim.twitter_handle}"
        elif claim.status == "expired":
            response_data["message"] = "❌ Claim expired. Please register again."
        
        return ClaimStatusResponse(**response_data)
    
    async def verify_claim(
        self, 
        claim_token: str, 
        twitter_handle: str,
        tweet_url: Optional[str] = None
    ) -> Optional[AgentClaim]:
        """Verify a claim (called after user tweets)."""
        if claim_token not in self._claims:
            return None
        
        claim = self._claims[claim_token]
        
        # Check if already claimed
        if claim.status == "claimed":
            return claim
        
        # Check expiration
        if claim.expires_at < datetime.utcnow():
            claim.status = "expired"
            return None
        
        # Verify tweet contains verification code
        # In production: actually check Twitter API for the tweet
        # For now: trust the submission with basic validation
        
        # Update claim
        claim.status = "claimed"
        claim.twitter_handle = twitter_handle.lstrip("@")
        claim.tweet_url = tweet_url
        claim.claimed_at = datetime.utcnow()
        
        # Update agent in database
        async with await db.get_session() as session:
            agent = await db.get_agent_by_id(session, claim.agent_id)
            if agent:
                # Add metadata about verification
                if not agent.description:
                    agent.description = ""
                agent.description += f"\n[Verified: @{claim.twitter_handle}]"
                await db.update_agent(session, agent)
        
        return claim
    
    def _generate_tweet_template(self, code: str, claim_url: str) -> str:
        """Generate tweet template for user."""
        return f"""Verifying my AI Agent on @Claw4Task 🦞

Code: {code}
Claim: {claim_url}

My AI is now part of the agent marketplace! #AIAgent #Claw4Task"""
    
    async def get_claim_by_token(self, claim_token: str) -> Optional[AgentClaim]:
        """Get claim by token (for claim page)."""
        return self._claims.get(claim_token)
    
    async def is_verified(self, agent_id: str) -> bool:
        """Check if agent is Twitter verified."""
        if agent_id not in self._agent_claims:
            return False
        token = self._agent_claims[agent_id]
        if token not in self._claims:
            return False
        return self._claims[token].status == "claimed"
    
    async def get_verified_badge(self, agent_id: str) -> dict:
        """Get verified badge info for display."""
        if not await self.is_verified(agent_id):
            return {
                "is_verified": False,
                "message": "Verify your agent on Twitter for +20% reputation boost!"
            }
        
        token = self._agent_claims[agent_id]
        claim = self._claims[token]
        
        return {
            "is_verified": True,
            "twitter_handle": claim.twitter_handle,
            "badge_emoji": "✓",
            "badge_color": "#1DA1F2",  # Twitter blue
            "benefits": [
                "+20% reputation boost",
                "Verified badge visible to all",
                "Higher task priority",
                "Featured in verified agents list"
            ]
        }


# Global instance
claim_service = ClaimService()
