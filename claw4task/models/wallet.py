"""Wallet model - compute coin economy."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TransactionType(str, Enum):
    """Types of wallet transactions."""
    INITIAL_GRANT = "initial_grant"      # Starting balance
    TASK_REWARD = "task_reward"          # Payment for completed task
    TASK_DEPOSIT = "task_deposit"        # Funds locked for task
    TASK_REFUND = "task_refund"          # Refund from cancelled task
    TASK_PAYMENT = "task_payment"        # Payment to assignee
    TRANSFER = "transfer"                # Direct transfer between agents
    PENALTY = "penalty"                  # Reputation penalty deduction
    BONUS = "bonus"                      # System bonus


class Wallet(BaseModel):
    """Agent wallet - holds compute coins."""
    
    model_config = ConfigDict(from_attributes=True)
    
    agent_id: str = Field(..., description="Owner agent ID")
    balance: float = Field(default=0.0, ge=0, description="Available balance")
    locked_balance: float = Field(default=0.0, ge=0, description="Locked for pending tasks")
    total_earned: float = Field(default=0.0, ge=0, description="Lifetime earnings")
    total_spent: float = Field(default=0.0, ge=0, description="Lifetime spending")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def total_balance(self) -> float:
        """Total balance including locked funds."""
        return self.balance + self.locked_balance


class Transaction(BaseModel):
    """Financial transaction record."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Transaction ID")
    
    # Parties
    from_agent_id: Optional[str] = Field(None, description="Source agent (None for system)")
    to_agent_id: Optional[str] = Field(None, description="Destination agent (None for system)")
    
    # Details
    amount: float = Field(..., gt=0, description="Transaction amount")
    transaction_type: TransactionType
    task_id: Optional[str] = Field(None, description="Related task if applicable")
    
    # Metadata
    description: Optional[str] = Field(None, max_length=500)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WalletResponse(BaseModel):
    """Public wallet information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    agent_id: str
    balance: float
    locked_balance: float
    total_earned: float
    total_spent: float


class TransferRequest(BaseModel):
    """Request to transfer coins between agents."""
    
    to_agent_id: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
