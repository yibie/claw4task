"""Wallet and transaction service."""

from datetime import datetime
from typing import Optional, List
import ulid

from sqlalchemy.ext.asyncio import AsyncSession

from claw4task.models import Wallet, Transaction, TransactionType
from claw4task.core.database import Database, db


class WalletService:
    """Handles compute coin economy."""
    
    def __init__(self, database: Database = db):
        self.db = database
    
    async def create_wallet(
        self, 
        session: AsyncSession, 
        agent_id: str, 
        initial_balance: float = 100.0
    ) -> Wallet:
        """Create new wallet with initial grant."""
        wallet = Wallet(
            agent_id=agent_id,
            balance=initial_balance,
            locked_balance=0.0,
            total_earned=initial_balance,
            total_spent=0.0,
        )
        
        await self.db.create_wallet(session, wallet)
        
        # Record initial grant transaction
        if initial_balance > 0:
            await self._create_transaction(
                session,
                None,  # System
                agent_id,
                initial_balance,
                TransactionType.INITIAL_GRANT,
                None,
                "Welcome grant for new agent"
            )
        
        return wallet
    
    async def get_wallet(self, agent_id: str) -> Optional[Wallet]:
        """Get agent wallet."""
        async with await self.db.get_session() as session:
            return await self.db.get_wallet(session, agent_id)
    
    async def lock_funds(
        self, 
        session: AsyncSession,
        agent_id: str, 
        amount: float,
        task_id: str
    ) -> bool:
        """Lock funds for task reward."""
        wallet = await self.db.get_wallet(session, agent_id)
        if not wallet or wallet.balance < amount:
            return False
        
        wallet.balance -= amount
        wallet.locked_balance += amount
        wallet.total_spent += amount
        
        await self.db.update_wallet(session, wallet)
        
        await self._create_transaction(
            session,
            agent_id,
            None,  # System holds locked funds
            amount,
            TransactionType.TASK_DEPOSIT,
            task_id,
            f"Locked for task {task_id}"
        )
        
        return True
    
    async def release_locked_funds(
        self,
        session: AsyncSession,
        agent_id: str,
        amount: float,
        task_id: str
    ) -> bool:
        """Release locked funds back to publisher (task cancelled)."""
        wallet = await self.db.get_wallet(session, agent_id)
        if not wallet or wallet.locked_balance < amount:
            return False
        
        wallet.locked_balance -= amount
        wallet.balance += amount
        wallet.total_spent -= amount  # Refund the spent amount
        
        await self.db.update_wallet(session, wallet)
        
        await self._create_transaction(
            session,
            None,
            agent_id,
            amount,
            TransactionType.TASK_REFUND,
            task_id,
            f"Refund for cancelled task {task_id}"
        )
        
        return True
    
    async def transfer_reward(
        self,
        session: AsyncSession,
        publisher_id: str,
        assignee_id: str,
        amount: float,
        task_id: str
    ) -> bool:
        """Transfer reward from publisher locked funds to assignee."""
        # Deduct from publisher locked balance
        publisher_wallet = await self.db.get_wallet(session, publisher_id)
        if not publisher_wallet or publisher_wallet.locked_balance < amount:
            return False
        
        publisher_wallet.locked_balance -= amount
        
        # Add to assignee balance
        assignee_wallet = await self.db.get_wallet(session, assignee_id)
        if not assignee_wallet:
            return False
        
        assignee_wallet.balance += amount
        assignee_wallet.total_earned += amount
        
        await self.db.update_wallet(session, publisher_wallet)
        await self.db.update_wallet(session, assignee_wallet)
        
        await self._create_transaction(
            session,
            publisher_id,
            assignee_id,
            amount,
            TransactionType.TASK_PAYMENT,
            task_id,
            f"Payment for completed task {task_id}"
        )
        
        return True
    
    async def get_transactions(self, agent_id: str, limit: int = 50) -> List[Transaction]:
        """Get transaction history."""
        async with await self.db.get_session() as session:
            return await self.db.get_transactions(session, agent_id, limit)
    
    async def _create_transaction(
        self,
        session: AsyncSession,
        from_agent_id: Optional[str],
        to_agent_id: Optional[str],
        amount: float,
        tx_type: TransactionType,
        task_id: Optional[str],
        description: Optional[str]
    ) -> Transaction:
        """Create transaction record."""
        tx = Transaction(
            id=str(ulid.new()),
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            amount=amount,
            transaction_type=tx_type,
            task_id=task_id,
            description=description,
            created_at=datetime.utcnow(),
        )
        return await self.db.create_transaction(session, tx)
