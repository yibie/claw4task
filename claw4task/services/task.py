"""Task lifecycle service."""

from datetime import datetime, timedelta
from typing import Optional, List
import ulid

from sqlalchemy.ext.asyncio import AsyncSession

from claw4task.models import (
    Task, TaskCreate, TaskSubmit, TaskProgressUpdate,
    TaskStatus, TaskResponse
)
from claw4task.services.wallet import WalletService
from claw4task.services.auth import AuthService
from claw4task.core.database import Database, db


class TaskService:
    """Handles task lifecycle."""
    
    def __init__(self, database: Database = db):
        self.db = database
        self.wallet_service = WalletService(database)
        self.auth_service = AuthService(database)
    
    async def create_task(
        self, 
        publisher_id: str, 
        create_data: TaskCreate
    ) -> Optional[Task]:
        """Create new task."""
        async with await self.db.get_session() as session:
            # Check publisher balance
            wallet = await self.db.get_wallet(session, publisher_id)
            if not wallet or wallet.balance < create_data.reward:
                return None
            
            # Lock funds
            locked = await self.wallet_service.lock_funds(
                session, publisher_id, create_data.reward, "temp"
            )
            if not locked:
                return None
            
            # Create task
            task = Task(
                id=str(ulid.new()),
                publisher_id=publisher_id,
                assignee_id=None,
                title=create_data.title,
                description=create_data.description,
                task_type=create_data.task_type,
                priority=create_data.priority,
                requirements=create_data.requirements,
                acceptance_criteria=create_data.acceptance_criteria,
                reward=create_data.reward,
                status=TaskStatus.OPEN,
                progress_updates=[],
                result=None,
                review_notes=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                deadline=create_data.deadline,
                claimed_at=None,
                submitted_at=None,
                completed_at=None,
                claim_timeout_minutes=create_data.claim_timeout_minutes,
                review_timeout_minutes=create_data.review_timeout_minutes,
            )
            
            await self.db.create_task(session, task)
            
            # Update transaction with actual task_id
            # (This is a bit hacky - in production, we'd create task first then lock)
            # For now, the locked funds are associated via task reference
            
            return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        async with await self.db.get_session() as session:
            return await self.db.get_task_by_id(session, task_id)
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        publisher_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        limit: int = 100
    ) -> List[TaskResponse]:
        """List tasks with filters."""
        async with await self.db.get_session() as session:
            tasks = await self.db.get_tasks(
                session,
                status=status.value if status else None,
                task_type=task_type,
                publisher_id=publisher_id,
                assignee_id=assignee_id,
                limit=limit
            )
            return [TaskResponse.model_validate(t) for t in tasks]
    
    async def claim_task(self, task_id: str, assignee_id: str) -> Optional[Task]:
        """Claim an open task."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.status != TaskStatus.OPEN:
                return None
            
            # Can't claim your own task
            if task.publisher_id == assignee_id:
                return None
            
            task.assignee_id = assignee_id
            task.status = TaskStatus.IN_PROGRESS
            task.claimed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            return task
    
    async def update_progress(
        self,
        task_id: str,
        assignee_id: str,
        update: TaskProgressUpdate
    ) -> Optional[Task]:
        """Update task progress."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.assignee_id != assignee_id:
                return None
            
            if task.status != TaskStatus.IN_PROGRESS:
                return None
            
            task.progress_updates.append({
                "progress_percent": update.progress_percent,
                "message": update.message,
                "metadata": update.metadata,
                "timestamp": datetime.utcnow().isoformat(),
            })
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            return task
    
    async def submit_task(
        self,
        task_id: str,
        assignee_id: str,
        submit_data: TaskSubmit
    ) -> Optional[Task]:
        """Submit completed task."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.assignee_id != assignee_id:
                return None
            
            if task.status != TaskStatus.IN_PROGRESS:
                return None
            
            task.result = submit_data.result
            task.status = TaskStatus.PENDING_REVIEW
            task.submitted_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            
            if submit_data.notes:
                task.review_notes = submit_data.notes
            
            await self.db.update_task(session, task)
            return task
    
    async def accept_task(
        self,
        task_id: str,
        publisher_id: str
    ) -> Optional[Task]:
        """Accept submitted task and release payment."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.publisher_id != publisher_id:
                return None
            
            if task.status != TaskStatus.PENDING_REVIEW:
                return None
            
            # Transfer reward
            transferred = await self.wallet_service.transfer_reward(
                session,
                publisher_id,
                task.assignee_id,
                task.reward,
                task_id
            )
            
            if not transferred:
                return None
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            
            # Update reputation
            await self.auth_service.update_reputation(
                task.assignee_id, success=True, reward=task.reward
            )
            
            return task
    
    async def reject_task(
        self,
        task_id: str,
        publisher_id: str,
        reason: Optional[str] = None
    ) -> Optional[Task]:
        """Reject submitted task."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.publisher_id != publisher_id:
                return None
            
            if task.status != TaskStatus.PENDING_REVIEW:
                return None
            
            # Return to open state or cancel
            # For simplicity, we'll return to OPEN for re-assignment
            task.status = TaskStatus.OPEN
            task.assignee_id = None
            task.result = None
            task.submitted_at = None
            task.review_notes = reason or "Task rejected"
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            
            # Penalize assignee
            await self.auth_service.update_reputation(
                task.assignee_id, success=False
            )
            
            return task
    
    async def cancel_task(
        self,
        task_id: str,
        publisher_id: str
    ) -> Optional[Task]:
        """Cancel open task and refund."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.publisher_id != publisher_id:
                return None
            
            if task.status not in [TaskStatus.OPEN, TaskStatus.IN_PROGRESS]:
                return None
            
            # Refund locked funds
            refunded = await self.wallet_service.release_locked_funds(
                session, publisher_id, task.reward, task_id
            )
            
            if not refunded:
                return None
            
            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            return task
    
    async def adjust_reward(
        self,
        task_id: str,
        new_reward: float,
        publisher_id: str
    ) -> Optional[Task]:
        """Adjust task reward. Handles fund locking/unlocking."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.publisher_id != publisher_id:
                return None
            
            if task.status not in [TaskStatus.OPEN, TaskStatus.IN_PROGRESS]:
                return None
            
            old_reward = task.reward
            difference = new_reward - old_reward
            
            if difference > 0:
                # Need to lock more funds
                locked = await self.wallet_service.lock_funds(
                    session, publisher_id, difference, task_id
                )
                if not locked:
                    return None
            elif difference < 0:
                # Return excess funds
                refunded = await self.wallet_service.release_locked_funds(
                    session, publisher_id, abs(difference), task_id
                )
                if not refunded:
                    return None
            
            # Update task reward
            task.reward = new_reward
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            return task
    
    async def check_expired_tasks(self) -> int:
        """Check and handle expired tasks. Returns count of processed tasks."""
        async with await self.db.get_session() as session:
            now = datetime.utcnow()
            count = 0
            
            # Get all in-progress tasks
            tasks = await self.db.get_tasks(session, status=TaskStatus.IN_PROGRESS.value)
            
            for task in tasks:
                if task.claimed_at:
                    deadline = task.claimed_at + timedelta(minutes=task.claim_timeout_minutes)
                    if now > deadline:
                        # Timeout - return to open
                        task.status = TaskStatus.OPEN
                        task.assignee_id = None
                        task.progress_updates.append({
                            "progress_percent": 0,
                            "message": "Task timed out and returned to open",
                            "timestamp": now.isoformat(),
                        })
                        await self.db.update_task(session, task)
                        count += 1
            
            # Check pending review tasks
            pending_tasks = await self.db.get_tasks(session, status=TaskStatus.PENDING_REVIEW.value)
            
            for task in pending_tasks:
                if task.submitted_at:
                    review_deadline = task.submitted_at + timedelta(minutes=task.review_timeout_minutes)
                    if now > review_deadline:
                        # Auto-accept
                        await self.accept_task(task.id, task.publisher_id)
                        count += 1
            
            return count
