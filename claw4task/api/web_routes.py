"""Web UI routes and stats API."""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from claw4task.core.database import db, TaskDB, AgentDB

router = APIRouter()
templates = Jinja2Templates(directory="claw4task/templates")


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(request: Request, task_id: str):
    """Task detail page - uses new visual design."""
    async with await db.get_session() as session:
        task = await db.get_task_by_id(session, task_id)
        if not task:
            return HTMLResponse(content="Task not found", status_code=404)
        
        # Get publisher info
        publisher = await db.get_agent_by_id(session, task.publisher_id)
        
        # Get assignee info if exists
        assignee = None
        if task.assignee_id:
            assignee = await db.get_agent_by_id(session, task.assignee_id)
        
        # Use new visual template
        template_name = "task_detail_v2.html" if hasattr(task, 'complexity_level') else "task_detail.html"
        
        return templates.TemplateResponse(template_name, {
            "request": request,
            "task": task,
            "publisher": publisher,
            "assignee": assignee
        })


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page - shows all task statuses."""
    async with await db.get_session() as session:
        # Get open tasks (available to claim)
        open_tasks = await db.get_tasks(session, status="open", limit=20)
        
        # Get pending review tasks (awaiting publisher acceptance)
        pending_review_tasks = await db.get_tasks(session, status="pending_review", limit=20)
        
        # Get in progress tasks
        in_progress_tasks = await db.get_tasks(session, status="in_progress", limit=20)
        
        # Get top agents by reputation
        from sqlalchemy import select, desc
        result = await session.execute(
            select(AgentDB)
            .order_by(desc(AgentDB.reputation_score))
            .limit(10)
        )
        top_agents = result.scalars().all()
        
        # Get stats
        stats = await get_stats_data(session)
        
        # Get recent activity
        activity = await get_recent_activity(session)
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "open_tasks": open_tasks,
            "pending_review_tasks": pending_review_tasks,
            "in_progress_tasks": in_progress_tasks,
            "top_agents": top_agents,
            "stats": stats,
            "recent_activity": activity
        })


@router.get("/api/web/stats")
async def web_stats() -> Dict[str, int]:
    """Get dashboard stats."""
    async with await db.get_session() as session:
        return await get_stats_data(session)


@router.get("/api/web/activity")
async def web_activity() -> List[Dict[str, Any]]:
    """Get recent activity."""
    async with await db.get_session() as session:
        return await get_recent_activity(session)


async def get_stats_data(session: AsyncSession) -> Dict[str, int]:
    """Calculate dashboard statistics."""
    from sqlalchemy import select, func
    
    # Open tasks
    result = await session.execute(
        select(func.count()).select_from(TaskDB).where(TaskDB.status == "open")
    )
    open_count = result.scalar()
    
    # In progress tasks
    result = await session.execute(
        select(func.count()).select_from(TaskDB).where(TaskDB.status == "in_progress")
    )
    in_progress_count = result.scalar()
    
    # Completed today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count())
        .select_from(TaskDB)
        .where(TaskDB.status == "completed")
        .where(TaskDB.completed_at >= today_start)
    )
    completed_today = result.scalar()
    
    # Active agents (created in last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    result = await session.execute(
        select(func.count())
        .select_from(AgentDB)
        .where(AgentDB.created_at >= week_ago)
    )
    active_agents = result.scalar()
    
    return {
        "open_tasks": open_count or 0,
        "in_progress_tasks": in_progress_count or 0,
        "completed_today": completed_today or 0,
        "active_agents": active_agents or 0
    }


async def get_recent_activity(session: AsyncSession) -> List[Dict[str, Any]]:
    """Generate recent activity feed."""
    from sqlalchemy import select, desc
    
    # Get recent tasks
    result = await session.execute(
        select(TaskDB)
        .order_by(desc(TaskDB.updated_at))
        .limit(20)
    )
    tasks = result.scalars().all()
    
    # Get agent names
    agent_ids = list(set([t.publisher_id for t in tasks]))
    agent_map = {}
    if agent_ids:
        result = await session.execute(
            select(AgentDB).where(AgentDB.id.in_(agent_ids))
        )
        for agent in result.scalars().all():
            agent_map[agent.id] = agent.name
    
    activities = []
    for task in tasks:
        action = ""
        if task.status == "open":
            action = "published a new task"
        elif task.status == "in_progress":
            action = "claimed a task"
        elif task.status == "pending_review":
            action = "submitted work for review"
        elif task.status == "completed":
            action = "completed a task"
        elif task.status == "rejected":
            action = "had work rejected"
        
        time_diff = datetime.utcnow() - task.updated_at
        time_ago = format_time_ago(time_diff)
        
        activities.append({
            "agent_name": agent_map.get(task.publisher_id, "Unknown"),
            "action": action,
            "time_ago": time_ago
        })
    
    return activities


def format_time_ago(diff: timedelta) -> str:
    """Format timedelta as human-readable string."""
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    else:
        days = seconds // 86400
        return f"{days}d ago"


@router.get("/blog", response_class=HTMLResponse)
@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog(request: Request, slug: str = ""):
    """Blog page."""
    # Default to first post if no slug
    if not slug:
        slug = "the-idea"
    
    return templates.TemplateResponse("blog.html", {
        "request": request,
        "slug": slug
    })
