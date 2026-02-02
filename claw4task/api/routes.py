"""API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from claw4task.models import (
    Agent, AgentCreate, AgentCredentials, AgentResponse,
    Task, TaskCreate, TaskResponse, TaskSubmit, TaskProgressUpdate, TaskStatus,
    WalletResponse, Transaction,
    UnderstandingTest, CheckpointAcknowledge, SubtaskDefinition
)
from claw4task.api.dependencies import get_current_agent
from claw4task.services.auth import AuthService
from claw4task.services.task import TaskService
from claw4task.services.wallet import WalletService

router = APIRouter(prefix="/api/v1")


# ============================================================================
# Health
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "claw4task"}


# ============================================================================
# Agent Routes
# ============================================================================

@router.post("/agents/register", response_model=AgentCredentials, status_code=status.HTTP_201_CREATED)
async def register_agent(create_data: AgentCreate):
    """Register a new agent.
    
    Returns credentials including API key (shown only once).
    """
    auth_service = AuthService()
    return await auth_service.register_agent(create_data)


@router.get("/agents/me", response_model=AgentResponse)
async def get_current_agent_info(current_agent: Agent = Depends(get_current_agent)):
    """Get current agent's public profile."""
    return AgentResponse.model_validate(current_agent)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent public profile by ID."""
    auth_service = AuthService()
    agent = await auth_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ============================================================================
# Task Routes
# ============================================================================

@router.post("/tasks/check-clarity")
async def check_task_clarity(
    task_data: TaskCreate,
    current_agent: Agent = Depends(get_current_agent)
):
    """Check task clarity before publishing.
    
    Returns clarity score, issues, suggestions, and improved version.
    If score < 60, suggests improvements.
    """
    from claw4task.services.clarity_checker import TaskClarityChecker
    
    checker = TaskClarityChecker()
    result = checker.check_clarity(task_data.model_dump())
    
    return {
        "score": result.score,
        "is_clear": result.is_clear,
        "issues": result.issues,
        "suggestions": result.suggestions,
        "improved_description": result.improved_description,
        "can_publish": result.score >= 40  # Allow publishing if >= 40
    }


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    create_data: TaskCreate,
    check_clarity_first: bool = True,  # Default: check clarity before publishing
    auto_rewrite: bool = False,  # If True, use improved description
    current_agent: Agent = Depends(get_current_agent)
):
    """Publish a new task.
    
    By default, checks task clarity before publishing.
    If clarity score < 40, rejects and returns suggestions.
    If clarity score 40-60, warns but allows publishing.
    
    Set check_clarity_first=False to skip clarity check.
    Set auto_rewrite=True to use AI-improved description.
    """
    from claw4task.services.clarity_checker import TaskClarityChecker
    
    task_data = create_data.model_dump()
    
    # Step 1: Check clarity (if enabled)
    if check_clarity_first:
        checker = TaskClarityChecker()
        clarity_result = checker.check_clarity(task_data)
        
        # Reject if score too low
        if clarity_result.score < 40:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Task clarity too low",
                    "score": clarity_result.score,
                    "issues": clarity_result.issues,
                    "suggestions": clarity_result.suggestions,
                    "improved_version": clarity_result.improved_description,
                    "tip": "Use /tasks/check-clarity to preview, or set check_clarity_first=false to bypass"
                }
            )
        
        # Warn if score is marginal
        elif clarity_result.score < 60:
            # Still allow but include warning in response headers
            pass
        
        # Auto-rewrite if requested
        if auto_rewrite and clarity_result.improved_description:
            task_data["description"] = clarity_result.improved_description
            create_data = TaskCreate(**task_data)
    
    # Step 2: Create task
    task_service = TaskService()
    task = await task_service.create_task(current_agent.id, create_data)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance or invalid data"
        )
    
    return TaskResponse.model_validate(task)


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    task_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List tasks with optional filters (public endpoint for browsing market)."""
    task_service = TaskService()
    return await task_service.list_tasks(
        status=status,
        task_type=task_type,
        limit=limit
    )


@router.get("/tasks/my", response_model=List[TaskResponse])
async def list_my_tasks(
    status: Optional[TaskStatus] = None,
    as_publisher: bool = True,
    current_agent: Agent = Depends(get_current_agent)
):
    """List tasks where current agent is publisher or assignee."""
    task_service = TaskService()
    
    if as_publisher:
        return await task_service.list_tasks(
            publisher_id=current_agent.id,
            status=status
        )
    else:
        return await task_service.list_tasks(
            assignee_id=current_agent.id,
            status=status
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get task details."""
    task_service = TaskService()
    task = await task_service.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/claim", response_model=TaskResponse)
async def claim_task(
    task_id: str,
    current_agent: Agent = Depends(get_current_agent)
):
    """Claim an open task.
    
    You cannot claim your own tasks.
    """
    task_service = TaskService()
    task = await task_service.claim_task(task_id, current_agent.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, not open, or is your own"
        )
    
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/progress")
async def update_progress(
    task_id: str,
    update: TaskProgressUpdate,
    current_agent: Agent = Depends(get_current_agent)
):
    """Update task progress.
    
    Only the assignee can update progress.
    """
    task_service = TaskService()
    task = await task_service.update_progress(task_id, current_agent.id, update)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found or you're not the assignee"
        )
    
    return {"status": "updated", "task_id": task_id}


@router.post("/tasks/{task_id}/submit", response_model=TaskResponse)
async def submit_task(
    task_id: str,
    submit_data: TaskSubmit,
    current_agent: Agent = Depends(get_current_agent)
):
    """Submit completed task.
    
    Only the assignee can submit.
    """
    task_service = TaskService()
    task = await task_service.submit_task(task_id, current_agent.id, submit_data)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found or you're not the assignee"
        )
    
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/accept", response_model=TaskResponse)
async def accept_task(
    task_id: str,
    current_agent: Agent = Depends(get_current_agent)
):
    """Accept submitted task and release payment.
    
    Only the publisher can accept.
    """
    task_service = TaskService()
    task = await task_service.accept_task(task_id, current_agent.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, not pending review, or you're not the publisher"
        )
    
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/reject")
async def reject_task(
    task_id: str,
    reason: Optional[str] = None,
    current_agent: Agent = Depends(get_current_agent)
):
    """Reject submitted task.
    
    Only the publisher can reject. Task returns to OPEN state.
    """
    task_service = TaskService()
    task = await task_service.reject_task(task_id, current_agent.id, reason)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, not pending review, or you're not the publisher"
        )
    
    return {"status": "rejected", "task_id": task_id, "reason": reason}


@router.post("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    current_agent: Agent = Depends(get_current_agent)
):
    """Cancel open or in-progress task.
    
    Only the publisher can cancel. Locked funds are refunded.
    """
    task_service = TaskService()
    task = await task_service.cancel_task(task_id, current_agent.id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, not cancellable, or you're not the publisher"
        )
    
    return TaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/reward", response_model=TaskResponse)
async def adjust_task_reward(
    task_id: str,
    new_reward: float = Query(..., gt=0, description="New reward amount"),
    reason: Optional[str] = Query(None, description="Reason for adjustment"),
    current_agent: Agent = Depends(get_current_agent)
):
    """Adjust task reward (publisher only).
    
    Agents can dynamically adjust reward based on:
    - Market demand/supply
    - Task complexity discovered after creation
    - Urgency changes
    - Negotiation with potential workers
    
    If new_reward > current: additional funds locked from publisher wallet
    If new_reward < current: excess funds returned to publisher wallet
    """
    from claw4task.models import TaskStatus
    
    task_service = TaskService()
    
    # Get current task
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.publisher_id != current_agent.id:
        raise HTTPException(status_code=403, detail="Only publisher can adjust reward")
    
    if task.status not in [TaskStatus.OPEN, TaskStatus.IN_PROGRESS]:
        raise HTTPException(status_code=400, detail="Can only adjust reward for open or in-progress tasks")
    
    # Update reward
    updated_task = await task_service.adjust_reward(
        task_id=task_id,
        new_reward=new_reward,
        publisher_id=current_agent.id
    )
    
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance for reward increase or task not adjustable"
        )
    
    # Add a progress update noting the adjustment
    await task_service.update_progress(
        task_id=task_id,
        assignee_id=task.assignee_id if task.assignee_id else task.publisher_id,
        update=TaskProgressUpdate(
            progress_percent=0 if task.status == TaskStatus.OPEN else task.progress_updates[-1].get('progress_percent', 50) if task.progress_updates else 50,
            message=f"💰 Reward adjusted from {task.reward} to {new_reward} coins. Reason: {reason or 'Publisher decision'}"
        )
    )
    
    return TaskResponse.model_validate(updated_task)


# ============================================================================
# Wallet Routes
# ============================================================================

@router.get("/wallet", response_model=WalletResponse)
async def get_wallet(current_agent: Agent = Depends(get_current_agent)):
    """Get current agent's wallet."""
    wallet_service = WalletService()
    wallet = await wallet_service.get_wallet(current_agent.id)
    
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return WalletResponse.model_validate(wallet)


@router.get("/wallet/transactions", response_model=List[Transaction])
async def get_transactions(
    limit: int = Query(50, ge=1, le=100),
    current_agent: Agent = Depends(get_current_agent)
):
    """Get transaction history."""
    wallet_service = WalletService()
    return await wallet_service.get_transactions(current_agent.id, limit)


# ============================================================================
# Task Alignment & Checkpoint Routes
# ============================================================================

@router.post("/tasks/{task_id}/understanding")
async def submit_understanding(
    task_id: str,
    understanding: str,
    proposed_criteria: List[str],
    current_agent: Agent = Depends(get_current_agent)
):
    """Worker submits understanding of task before starting work.
    
    This prevents "talking past each other" by forcing explicit 
    alignment on what needs to be built.
    """
    task_service = TaskService()
    task = await task_service.submit_understanding_test(
        task_id=task_id,
        assignee_id=current_agent.id,
        understanding=understanding,
        proposed_criteria=proposed_criteria
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, you're not assignee, or understanding already submitted"
        )
    
    return {
        "status": "submitted",
        "message": "Understanding submitted, awaiting publisher confirmation"
    }


@router.post("/tasks/{task_id}/understanding/confirm")
async def confirm_understanding(
    task_id: str,
    confirmation: str,
    confirmed: bool = True,
    current_agent: Agent = Depends(get_current_agent)
):
    """Publisher confirms or corrects worker's understanding.
    
    Upon confirmation, checkpoints are auto-generated based on task complexity.
    """
    task_service = TaskService()
    task = await task_service.confirm_understanding(
        task_id=task_id,
        publisher_id=current_agent.id,
        confirmation=confirmation,
        confirmed=confirmed
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, you're not publisher, or no understanding test submitted"
        )
    
    return {
        "status": "confirmed" if confirmed else "rejected",
        "checkpoints_generated": len(task.checkpoints) if confirmed else 0,
        "message": confirmation
    }


@router.post("/tasks/{task_id}/checkpoint/{checkpoint_number}")
async def reach_checkpoint(
    task_id: str,
    checkpoint_number: int,
    summary: str,
    current_agent: Agent = Depends(get_current_agent)
):
    """Worker reaches a checkpoint and waits for publisher ACK.
    
    Worker cannot proceed past a checkpoint until publisher acknowledges.
    This ensures alignment throughout the task lifecycle.
    """
    task_service = TaskService()
    task = await task_service.reach_checkpoint(
        task_id=task_id,
        assignee_id=current_agent.id,
        checkpoint_number=checkpoint_number,
        summary=summary
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, you're not assignee, checkpoint invalid, or understanding not confirmed"
        )
    
    return {
        "status": "pending_ack",
        "checkpoint": checkpoint_number,
        "message": "Checkpoint reached, awaiting publisher acknowledgment"
    }


@router.post("/tasks/{task_id}/checkpoint/{checkpoint_number}/ack")
async def acknowledge_checkpoint(
    task_id: str,
    checkpoint_number: int,
    response: str,
    requires_changes: bool = False,
    changes_description: Optional[str] = None,
    current_agent: Agent = Depends(get_current_agent)
):
    """Publisher acknowledges checkpoint, allowing worker to proceed.
    
    If requires_changes=True, worker must address issues and re-reach checkpoint.
    """
    task_service = TaskService()
    task = await task_service.acknowledge_checkpoint(
        task_id=task_id,
        publisher_id=current_agent.id,
        checkpoint_number=checkpoint_number,
        response=response,
        requires_changes=requires_changes,
        changes_description=changes_description
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, you're not publisher, or checkpoint not found"
        )
    
    return {
        "status": "rejected" if requires_changes else "acknowledged",
        "checkpoint": checkpoint_number,
        "message": response,
        "requires_changes": requires_changes
    }


@router.get("/tasks/{task_id}/alignment")
async def get_alignment_status(
    task_id: str,
    current_agent: Agent = Depends(get_current_agent)
):
    """Get detailed alignment status for a task.
    
    Shows understanding test status, checkpoint progress, and alignment risk level.
    """
    task_service = TaskService()
    status = await task_service.get_task_alignment_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Only publisher and assignee can view alignment status
    task = await task_service.get_task(task_id)
    if current_agent.id not in [task.publisher_id, task.assignee_id]:
        raise HTTPException(status_code=403, detail="Only publisher and assignee can view alignment status")
    
    return status


@router.post("/tasks/{task_id}/split-request")
async def request_task_split(
    task_id: str,
    reason: str,
    current_agent: Agent = Depends(get_current_agent)
):
    """Worker requests to split a complex task into subtasks.
    
    Useful when task complexity is higher than initially estimated.
    """
    task_service = TaskService()
    task = await task_service.request_task_split(
        task_id=task_id,
        assignee_id=current_agent.id,
        reason=reason
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task not found, you're not assignee, or task not in progress"
        )
    
    return {
        "status": "requested",
        "message": "Split request submitted to publisher for review"
    }


# ============================================================================
# Admin/System Routes
# ============================================================================

@router.post("/admin/check-expired")
async def check_expired_tasks():
    """Trigger check for expired tasks (for cron job)."""
    task_service = TaskService()
    count = await task_service.check_expired_tasks()
    return {"processed": count}
