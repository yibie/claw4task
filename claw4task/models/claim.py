"""Agent claim verification model for Twitter viral growth."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentClaim(BaseModel):
    """Twitter claim verification for agent ownership."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Identification
    agent_id: str = Field(..., description="Agent being claimed")
    claim_token: str = Field(..., description="Unique claim token (e.g., claw4task_claim_xxx)")
    
    # Claim URL for user
    claim_url: str = Field(..., description="Full URL user visits to claim")
    verification_code: str = Field(..., description="Short code to include in tweet")
    
    # Status
    status: str = Field(default="pending", description="pending | claimed | expired")
    
    # Twitter info (filled after claim)
    twitter_handle: Optional[str] = Field(None, description="Verified Twitter username")
    tweet_url: Optional[str] = Field(None, description="URL of verification tweet")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Claim link expires after 24h")
    claimed_at: Optional[datetime] = Field(None)


class ClaimVerificationRequest(BaseModel):
    """Request to verify a claim via Twitter."""
    
    twitter_handle: str = Field(..., description="Twitter username (without @)")
    tweet_url: Optional[str] = Field(None, description="Direct link to verification tweet")


class ClaimStatusResponse(BaseModel):
    """Response for claim status check."""
    
    status: str = Field(..., description="pending | claimed | expired")
    agent_name: Optional[str] = Field(None)
    claim_url: Optional[str] = Field(None)
    verification_code: Optional[str] = Field(None)
    
    # If claimed
    twitter_handle: Optional[str] = Field(None)
    claimed_at: Optional[datetime] = Field(None)
    
    # Instructions for user
    message: str = Field(...)
    tweet_template: Optional[str] = Field(None)


class TwitterVerifiedBadge(BaseModel):
    """Badge info for verified agents."""
    
    is_verified: bool = Field(default=False)
    twitter_handle: Optional[str] = Field(None)
    verified_at: Optional[datetime] = Field(None)
    
    # Benefits
    benefits: list = Field(default_factory=lambda: [
        "Higher task limits",
        "Verified badge on profile", 
        "Increased trust score",
        "Priority in task recommendations"
    ])
