"""Task lifecycle service."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
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
        """Create new task with atomic balance check and fund locking."""
        async with await self.db.get_session() as session:
            # Step 1: Generate task ID first
            task_id = str(ulid.new())
            
            # Step 2: Lock funds with actual task_id (atomic operation)
            locked = await self.wallet_service.lock_funds(
                session, publisher_id, create_data.reward, task_id
            )
            if not locked:
                return None
            
            # Step 3: Create task with the same ID
            task = Task(
                id=task_id,
                publisher_id=publisher_id,
                assignee_id=None,
                title=create_data.title,
                description=create_data.description,
                task_type=create_data.task_type,
                priority=create_data.priority,
                requirements=create_data.requirements,
                acceptance_criteria=create_data.acceptance_criteria,
                deliverables=create_data.deliverables if hasattr(create_data, 'deliverables') else [],
                examples=create_data.examples if hasattr(create_data, 'examples') else [],
                reference_links=create_data.reference_links if hasattr(create_data, 'reference_links') else [],
                notes_for_ai=create_data.notes_for_ai if hasattr(create_data, 'notes_for_ai') else None,
                required_capabilities=create_data.required_capabilities if hasattr(create_data, 'required_capabilities') else [],
                estimated_hours=create_data.estimated_hours if hasattr(create_data, 'estimated_hours') else None,
                complexity_level=create_data.complexity_level if hasattr(create_data, 'complexity_level') else 3,
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
    
    # ========== CHECKPOINT & ALIGNMENT SYSTEM ==========
    
    def _calculate_complexity(self, task: Task) -> int:
        """Calculate task complexity score (1-10) based on description and requirements."""
        complexity = 1
        
        # Length-based complexity
        desc_length = len(task.description)
        if desc_length > 2000:
            complexity += 3
        elif desc_length > 1000:
            complexity += 2
        elif desc_length > 500:
            complexity += 1
        
        # Requirements complexity
        req_count = len(task.requirements)
        if req_count > 5:
            complexity += 2
        elif req_count > 2:
            complexity += 1
        
        # Acceptance criteria complexity
        criteria_count = len(task.acceptance_criteria)
        if criteria_count > 3:
            complexity += 2
        elif criteria_count > 1:
            complexity += 1
        
        return min(complexity, 10)
    
    def _generate_checkpoints(self, complexity: int) -> List[Dict]:
        """Generate checkpoint structure based on complexity."""
        if complexity <= 3:
            # Simple task: 2 checkpoints
            checkpoints = [
                {"checkpoint_number": 1, "target_percent": 30, "status": "pending"},
                {"checkpoint_number": 2, "target_percent": 100, "status": "pending"},
            ]
        elif complexity <= 6:
            # Medium task: 3 checkpoints
            checkpoints = [
                {"checkpoint_number": 1, "target_percent": 25, "status": "pending"},
                {"checkpoint_number": 2, "target_percent": 60, "status": "pending"},
                {"checkpoint_number": 3, "target_percent": 100, "status": "pending"},
            ]
        else:
            # Complex task: 4 checkpoints
            checkpoints = [
                {"checkpoint_number": 1, "target_percent": 20, "status": "pending"},
                {"checkpoint_number": 2, "target_percent": 45, "status": "pending"},
                {"checkpoint_number": 3, "target_percent": 75, "status": "pending"},
                {"checkpoint_number": 4, "target_percent": 100, "status": "pending"},
            ]
        
        return checkpoints
    
    async def submit_understanding_test(
        self,
        task_id: str,
        assignee_id: str,
        understanding: str,
        proposed_criteria: List[str]
    ) -> Optional[Task]:
        """Worker submits their understanding of the task before starting work."""
        from claw4task.models import UnderstandingTest
        
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.assignee_id != assignee_id:
                return None
            
            if task.status != TaskStatus.IN_PROGRESS:
                return None
            
            # Create understanding test
            test = UnderstandingTest(
                worker_understanding=understanding,
                proposed_criteria=proposed_criteria,
                confirmed=False
            )
            
            task.understanding_test = test.model_dump()
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            return task
    
    async def confirm_understanding(
        self,
        task_id: str,
        publisher_id: str,
        confirmation: str,
        confirmed: bool = True
    ) -> Optional[Task]:
        """Publisher confirms or corrects worker's understanding."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.publisher_id != publisher_id:
                return None
            
            if not task.understanding_test:
                return None
            
            # Update understanding test
            task.understanding_test["publisher_confirmation"] = confirmation
            task.understanding_test["confirmed"] = confirmed
            task.understanding_test["confirmed_at"] = datetime.utcnow().isoformat()
            
            if confirmed:
                # Generate checkpoints based on complexity
                complexity = self._calculate_complexity(task)
                task.complexity_score = complexity
                task.checkpoints = self._generate_checkpoints(complexity)
                task.current_checkpoint = 0
            
            task.updated_at = datetime.utcnow()
            await self.db.update_task(session, task)
            return task
    
    async def reach_checkpoint(
        self,
        task_id: str,
        assignee_id: str,
        checkpoint_number: int,
        summary: str,
        result_snapshot: Optional[Dict] = None
    ) -> Optional[Task]:
        """Worker reaches a checkpoint and waits for publisher ACK."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.assignee_id != assignee_id:
                return None
            
            if task.status != TaskStatus.IN_PROGRESS:
                return None
            
            # Must have confirmed understanding first
            if not task.understanding_test or not task.understanding_test.get("confirmed"):
                return None
            
            # Find the checkpoint
            checkpoint = None
            for cp in task.checkpoints:
                if cp["checkpoint_number"] == checkpoint_number:
                    checkpoint = cp
                    break
            
            if not checkpoint:
                return None
            
            # Update checkpoint
            checkpoint["status"] = "pending"
            checkpoint["worker_summary"] = summary
            checkpoint["result_snapshot"] = result_snapshot
            checkpoint["reached_at"] = datetime.utcnow().isoformat()
            
            task.current_checkpoint = checkpoint_number
            task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, task)
            return task
    
    async def acknowledge_checkpoint(
        self,
        task_id: str,
        publisher_id: str,
        checkpoint_number: int,
        response: str,
        requires_changes: bool = False,
        changes_description: Optional[str] = None
    ) -> Optional[Task]:
        """Publisher acknowledges checkpoint, allowing worker to proceed."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.publisher_id != publisher_id:
                return None
            
            # Find the checkpoint
            checkpoint = None
            for cp in task.checkpoints:
                if cp["checkpoint_number"] == checkpoint_number:
                    checkpoint = cp
                    break
            
            if not checkpoint:
                return None
            
            # Update checkpoint
            checkpoint["publisher_response"] = response
            checkpoint["requires_changes"] = requires_changes
            checkpoint["acknowledged_at"] = datetime.utcnow().isoformat()
            
            if requires_changes:
                checkpoint["status"] = "rejected"
                # Don't update current_checkpoint - worker must fix and re-reach
            else:
                checkpoint["status"] = "acknowledged"
                # Move to next checkpoint
                task.current_checkpoint = checkpoint_number
            
            task.updated_at = datetime.utcnow()
            await self.db.update_task(session, task)
            return task
    
    async def request_task_split(
        self,
        task_id: str,
        assignee_id: str,
        reason: str
    ) -> Optional[Task]:
        """Worker requests to split a complex task into subtasks."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            
            if not task or task.assignee_id != assignee_id:
                return None
            
            if task.status != TaskStatus.IN_PROGRESS:
                return None
            
            # Mark task as needing split review by publisher
            task.progress_updates.append({
                "type": "split_request",
                "message": reason,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            task.updated_at = datetime.utcnow()
            await self.db.update_task(session, task)
            return task
    
    async def split_task(
        self,
        task_id: str,
        publisher_id: str,
        subtask_definitions: List[Dict]
    ) -> Optional[List[Task]]:
        """Publisher splits a task into subtasks."""
        async with await self.db.get_session() as session:
            original_task = await self.db.get_task_by_id(session, task_id)
            
            if not original_task or original_task.publisher_id != publisher_id:
                return None
            
            if original_task.status not in [TaskStatus.OPEN, TaskStatus.IN_PROGRESS]:
                return None
            
            subtasks = []
            total_reward = sum(st["reward"] for st in subtask_definitions)
            
            # Validate total reward doesn't exceed original
            if total_reward > original_task.reward:
                return None
            
            for st_def in subtask_definitions:
                subtask = Task(
                    id=str(ulid.new()),
                    publisher_id=publisher_id,
                    assignee_id=None,
                    title=st_def["title"],
                    description=st_def["description"],
                    task_type=original_task.task_type,
                    priority=original_task.priority,
                    requirements=st_def.get("requirements", {}),
                    acceptance_criteria={"criteria": st_def.get("acceptance_criteria", [])},
                    reward=st_def["reward"],
                    status=TaskStatus.OPEN,
                    progress_updates=[],
                    result=None,
                    review_notes=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    deadline=original_task.deadline,
                    claimed_at=None,
                    submitted_at=None,
                    completed_at=None,
                    claim_timeout_minutes=original_task.claim_timeout_minutes,
                    review_timeout_minutes=original_task.review_timeout_minutes,
                    parent_task_id=original_task.id,
                    subtask_ids=[],
                    checkpoints=[],
                    understanding_test=None,
                    current_checkpoint=0,
                    complexity_score=3,  # Subtasks are simpler
                    dialogue_message_count=0,
                )
                
                await self.db.create_task(session, subtask)
                subtasks.append(subtask)
                original_task.subtask_ids.append(subtask.id)
            
            # Cancel original task and refund remaining funds
            remaining_reward = original_task.reward - total_reward
            if remaining_reward > 0:
                await self.wallet_service.release_locked_funds(
                    session, publisher_id, remaining_reward, task_id
                )
            
            original_task.status = TaskStatus.CANCELLED
            original_task.review_notes = f"Split into {len(subtasks)} subtasks"
            original_task.updated_at = datetime.utcnow()
            
            await self.db.update_task(session, original_task)
            return subtasks
    
    async def get_task_alignment_status(self, task_id: str) -> Optional[Dict]:
        """Get detailed alignment status for a task."""
        async with await self.db.get_session() as session:
            task = await self.db.get_task_by_id(session, task_id)
            if not task:
                return None
            
            return {
                "task_id": task.id,
                "status": task.status,
                "complexity_score": task.complexity_score,
                "dialogue_message_count": task.dialogue_message_count,
                "understanding_confirmed": (
                    task.understanding_test.get("confirmed", False)
                    if task.understanding_test else False
                ),
                "current_checkpoint": task.current_checkpoint,
                "total_checkpoints": len(task.checkpoints),
                "checkpoints": task.checkpoints,
                "alignment_risk": self._calculate_alignment_risk(task)
            }
    
    def _calculate_alignment_risk(self, task: Task) -> str:
        """Calculate alignment risk level."""
        if not task.understanding_test:
            return "high"  # No understanding test submitted
        
        if not task.understanding_test.get("confirmed"):
            return "high"  # Understanding not confirmed
        
        # Check for rejected checkpoints
        rejected = sum(1 for cp in task.checkpoints if cp.get("status") == "rejected")
        if rejected >= 2:
            return "high"
        if rejected == 1:
            return "medium"
        
        # Check dialogue volume
        if task.dialogue_message_count > 20:
            return "medium"  # Lots of back-and-forth suggests confusion
        
        return "low"
