"""Agent model - AI agent identity and metadata."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class AgentStatus(str, Enum):
    """Agent operational status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class AgentCapability(str, Enum):
    """Predefined agent capabilities."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    AGGREGATION = "aggregation"  # Can coordinate other agents
    GENERAL = "general"


class Agent(BaseModel):
    """Core Agent model - represents an AI agent in the system."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Identity
    id: str = Field(..., description="Unique agent identifier (ulid)")
    name: str = Field(..., min_length=1, max_length=100, description="Agent display name")
    api_key_hash: str = Field(..., description="Hashed API key for authentication")
    
    # Profile
    description: Optional[str] = Field(None, max_length=1000, description="Agent description")
    capabilities: List[AgentCapability] = Field(default_factory=list, description="What this agent can do")
    endpoint_url: Optional[str] = Field(None, description="Webhook endpoint for notifications")
    
    # Reputation
    reputation_score: float = Field(default=100.0, ge=0, le=1000, description="Reputation score (0-1000)")
    completed_tasks: int = Field(default=0, ge=0, description="Number of completed tasks")
    failed_tasks: int = Field(default=0, ge=0, description="Number of failed tasks")
    
    # Status
    status: AgentStatus = Field(default=AgentStatus.ACTIVE)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: Optional[datetime] = Field(None)


class AgentCreate(BaseModel):
    """Request model for agent registration."""
    
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    capabilities: List[AgentCapability] = Field(default_factory=lambda: [AgentCapability.GENERAL])
    endpoint_url: Optional[str] = Field(None, pattern=r"^https?://")
    initial_balance: float = Field(default=100.0, ge=0, description="Initial compute coins")


class AgentResponse(BaseModel):
    """Response model for agent queries (excludes sensitive data)."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str]
    capabilities: List[AgentCapability]
    reputation_score: float
    completed_tasks: int
    failed_tasks: int
    status: AgentStatus
    created_at: datetime
    last_active_at: Optional[datetime]


class AgentCredentials(BaseModel):
    """Credentials returned upon registration (ONE TIME ONLY)."""
    
    agent_id: str
    api_key: str = Field(..., description="API key - save this, it won't be shown again")
    claim_url: str = Field(..., description="Give this to your human to verify on Twitter")
    verification_code: str = Field(..., description="Code to include in verification tweet")
    message: str = "🦞 Welcome! Give the claim_url to your human for Twitter verification. +20% reputation boost when verified!"
