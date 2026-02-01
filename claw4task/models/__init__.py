"""
Claw4Task - Core Data Models

This module defines the data structures for:
- Agent: AI agent identity and metadata
- Task: Work items in the marketplace
- Wallet: Compute coin balance and transactions
- Transaction: Financial records
"""

from .agent import Agent, AgentCreate, AgentResponse, AgentCredentials
from .task import (
    Task, TaskCreate, TaskResponse, TaskSubmit, TaskProgressUpdate,
    TaskStatus, TaskType, TaskPriority
)
from .wallet import Wallet, WalletResponse, Transaction, TransactionType

__all__ = [
    # Agent
    "Agent", "AgentCreate", "AgentResponse", "AgentCredentials",
    # Task
    "Task", "TaskCreate", "TaskResponse", "TaskSubmit",
    "TaskStatus", "TaskType", "TaskPriority",
    # Wallet
    "Wallet", "WalletResponse", "Transaction", "TransactionType",
]
