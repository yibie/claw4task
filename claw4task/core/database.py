"""Database layer - SQLite with SQLAlchemy."""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, select, update
from datetime import datetime
import json
from typing import Optional, List

from claw4task.models import Agent, Task, Wallet, Transaction

# Use environment variable for database path, default to local file
# In Fly.io: /data/claw4task.db (persisted volume)
# Local: ./claw4task.db
DATABASE_PATH = os.getenv("DATABASE_PATH", "./claw4task.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

Base = declarative_base()


class AgentDB(Base):
    """Agent database table."""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    api_key_hash = Column(String, nullable=False)
    description = Column(String)
    capabilities = Column(JSON, default=list)
    endpoint_url = Column(String)
    reputation_score = Column(Float, default=100.0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime)


class TaskDB(Base):
    """Task database table."""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    publisher_id = Column(String, nullable=False, index=True)
    assignee_id = Column(String, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    priority = Column(Integer, default=2)
    requirements = Column(JSON, default=dict)
    acceptance_criteria = Column(JSON, default=dict)
    reward = Column(Float, nullable=False)
    status = Column(String, default="open", index=True)
    progress_updates = Column(JSON, default=list)
    result = Column(JSON)
    review_notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime)
    claimed_at = Column(DateTime)
    submitted_at = Column(DateTime)
    completed_at = Column(DateTime)
    claim_timeout_minutes = Column(Integer, default=60)
    review_timeout_minutes = Column(Integer, default=30)
    
    # Checkpoint system for preventing misalignment
    checkpoints = Column(JSON, default=list)
    understanding_test = Column(JSON)
    current_checkpoint = Column(Integer, default=0)
    
    # Complexity tracking for auto-splitting
    complexity_score = Column(Integer, default=1)
    dialogue_message_count = Column(Integer, default=0)
    
    # Task splitting support
    parent_task_id = Column(String, index=True)
    subtask_ids = Column(JSON, default=list)


class WalletDB(Base):
    """Wallet database table."""
    __tablename__ = "wallets"
    
    agent_id = Column(String, primary_key=True)
    balance = Column(Float, default=0.0)
    locked_balance = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TransactionDB(Base):
    """Transaction database table."""
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True)
    from_agent_id = Column(String, index=True)
    to_agent_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    task_id = Column(String, index=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Database:
    """Database manager."""
    
    def __init__(self, database_url: str = None):
        url = database_url or DATABASE_URL
        self.engine = create_async_engine(url, echo=False)
        self.session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init(self):
        """Create tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        return self.session_maker()
    
    # Agent operations
    async def create_agent(self, session: AsyncSession, agent: Agent) -> Agent:
        """Create new agent."""
        db_agent = AgentDB(**agent.model_dump())
        session.add(db_agent)
        await session.commit()
        return agent
    
    async def get_agent_by_id(self, session: AsyncSession, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        result = await session.execute(select(AgentDB).where(AgentDB.id == agent_id))
        db_agent = result.scalar_one_or_none()
        return Agent.model_validate(db_agent) if db_agent else None
    
    async def get_agent_by_api_key_hash(self, session: AsyncSession, api_key_hash: str) -> Optional[Agent]:
        """Get agent by API key hash."""
        result = await session.execute(
            select(AgentDB).where(AgentDB.api_key_hash == api_key_hash)
        )
        db_agent = result.scalar_one_or_none()
        return Agent.model_validate(db_agent) if db_agent else None
    
    async def update_agent(self, session: AsyncSession, agent: Agent) -> Agent:
        """Update agent."""
        agent.updated_at = datetime.utcnow()
        db_agent = AgentDB(**agent.model_dump())
        await session.merge(db_agent)
        await session.commit()
        return agent
    
    # Task operations
    async def create_task(self, session: AsyncSession, task: Task) -> Task:
        """Create new task."""
        db_task = TaskDB(**task.model_dump())
        session.add(db_task)
        await session.commit()
        return task
    
    async def get_task_by_id(self, session: AsyncSession, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        result = await session.execute(select(TaskDB).where(TaskDB.id == task_id))
        db_task = result.scalar_one_or_none()
        return Task.model_validate(db_task) if db_task else None
    
    async def get_tasks(
        self, 
        session: AsyncSession, 
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        publisher_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """Query tasks with filters."""
        query = select(TaskDB)
        
        if status:
            query = query.where(TaskDB.status == status)
        if task_type:
            query = query.where(TaskDB.task_type == task_type)
        if publisher_id:
            query = query.where(TaskDB.publisher_id == publisher_id)
        if assignee_id:
            query = query.where(TaskDB.assignee_id == assignee_id)
        
        query = query.order_by(TaskDB.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        return [Task.model_validate(t) for t in result.scalars().all()]
    
    async def update_task(self, session: AsyncSession, task: Task) -> Task:
        """Update task."""
        task.updated_at = datetime.utcnow()
        db_task = TaskDB(**task.model_dump())
        await session.merge(db_task)
        await session.commit()
        return task
    
    # Wallet operations
    async def create_wallet(self, session: AsyncSession, wallet: Wallet) -> Wallet:
        """Create new wallet."""
        db_wallet = WalletDB(**wallet.model_dump())
        session.add(db_wallet)
        await session.commit()
        return wallet
    
    async def get_wallet(self, session: AsyncSession, agent_id: str) -> Optional[Wallet]:
        """Get wallet by agent ID."""
        result = await session.execute(select(WalletDB).where(WalletDB.agent_id == agent_id))
        db_wallet = result.scalar_one_or_none()
        return Wallet.model_validate(db_wallet) if db_wallet else None
    
    async def update_wallet(self, session: AsyncSession, wallet: Wallet) -> Wallet:
        """Update wallet."""
        wallet.updated_at = datetime.utcnow()
        db_wallet = WalletDB(**wallet.model_dump())
        await session.merge(db_wallet)
        await session.commit()
        return wallet
    
    # Transaction operations
    async def create_transaction(self, session: AsyncSession, transaction: Transaction) -> Transaction:
        """Create transaction record."""
        db_tx = TransactionDB(**transaction.model_dump())
        session.add(db_tx)
        await session.commit()
        return transaction
    
    async def get_transactions(
        self,
        session: AsyncSession,
        agent_id: str,
        limit: int = 50
    ) -> List[Transaction]:
        """Get transactions for an agent."""
        result = await session.execute(
            select(TransactionDB)
            .where(
                (TransactionDB.from_agent_id == agent_id) | 
                (TransactionDB.to_agent_id == agent_id)
            )
            .order_by(TransactionDB.created_at.desc())
            .limit(limit)
        )
        return [Transaction.model_validate(t) for t in result.scalars().all()]


# Global database instance
db = Database()
