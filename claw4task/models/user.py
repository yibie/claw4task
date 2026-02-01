"""Human user model for web interface login."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class User(BaseModel):
    """Human user account for managing agents."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Unique user ID")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password_hash: str = Field(..., description="Hashed password")
    
    # Profile
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None)
    
    # Relationships
    agent_ids: List[str] = Field(default_factory=list, description="IDs of user's agents")
    
    # Status
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(None)
    

class UserCreate(BaseModel):
    """Request model for user registration."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=6, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Request model for user login."""
    
    username: str
    password: str


class UserResponse(BaseModel):
    """User info (excludes sensitive data)."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    username: str
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    agent_ids: List[str]
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]


class UserSession(BaseModel):
    """Session data for logged-in user."""
    
    user_id: str
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
