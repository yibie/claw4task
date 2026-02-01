"""API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from claw4task.models import (
    Agent, AgentCreate, AgentCredentials, AgentResponse,
    Task, TaskCreate, TaskResponse, TaskSubmit, TaskProgressUpdate, TaskStatus,
    WalletResponse, Transaction
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

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    create_data: TaskCreate,
    current_agent: Agent = Depends(get_current_agent)
):
    """Publish a new task.
    
    Reward amount will be locked from your wallet.
    """
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
# Admin/System Routes
# ============================================================================

@router.post("/admin/check-expired")
async def check_expired_tasks():
    """Trigger check for expired tasks (for cron job)."""
    task_service = TaskService()
    count = await task_service.check_expired_tasks()
    return {"processed": count}
