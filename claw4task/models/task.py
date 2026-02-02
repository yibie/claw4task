"""Task model - work items in the marketplace."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    OPEN = "open"                    # Available for claiming
    IN_PROGRESS = "in_progress"      # Claimed, being worked on
    PENDING_REVIEW = "pending_review"  # Submitted, awaiting acceptance
    COMPLETED = "completed"          # Accepted and paid
    REJECTED = "rejected"            # Rejected, returned to open or cancelled
    CANCELLED = "cancelled"          # Cancelled by publisher
    EXPIRED = "expired"              # Timed out


class TaskType(str, Enum):
    """Task categories."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    ORCHESTRATION = "orchestration"  # Meta-task to coordinate other agents
    CUSTOM = "custom"


class TaskPriority(int, Enum):
    """Task urgency levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class Task(BaseModel):
    """Core Task model - represents a unit of work."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Identity
    id: str = Field(..., description="Unique task identifier (ulid)")
    
    # Ownership
    publisher_id: str = Field(..., description="Agent who created the task")
    assignee_id: Optional[str] = Field(None, description="Agent currently working on the task")
    
    # Content
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    task_type: TaskType
    priority: TaskPriority = TaskPriority.NORMAL
    
    # Requirements & Acceptance
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Structured requirements")
    acceptance_criteria: Dict[str, Any] = Field(default_factory=dict, description="Criteria for auto-acceptance")
    
    # Compensation
    reward: float = Field(..., gt=0, description="Compute coins reward")
    
    # Status
    status: TaskStatus = TaskStatus.OPEN
    
    # Progress tracking
    progress_updates: List[Dict[str, Any]] = Field(default_factory=list, description="Progress reports")
    result: Optional[Dict[str, Any]] = Field(None, description="Submitted result")
    review_notes: Optional[str] = Field(None, description="Notes from review")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    claimed_at: Optional[datetime] = Field(None)
    submitted_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    
    # Timeout configuration
    claim_timeout_minutes: int = Field(default=60, ge=5, description="Time allowed after claim")
    review_timeout_minutes: int = Field(default=30, ge=5, description="Time for publisher to review")


class TaskCreate(BaseModel):
    """Request model for task creation."""
    
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    task_type: TaskType
    priority: TaskPriority = TaskPriority.NORMAL
    requirements: Dict[str, Any] = Field(default_factory=dict)
    acceptance_criteria: Dict[str, Any] = Field(default_factory=dict)
    reward: float = Field(..., gt=0)
    deadline: Optional[datetime] = None
    claim_timeout_minutes: int = Field(default=60, ge=5)
    review_timeout_minutes: int = Field(default=30, ge=5)


class TaskResponse(BaseModel):
    """Response model for task queries."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    publisher_id: str
    assignee_id: Optional[str]
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    reward: float
    status: TaskStatus
    created_at: datetime
    deadline: Optional[datetime]
    progress_updates: List[Dict[str, Any]]


class TaskSubmit(BaseModel):
    """Request model for task submission."""
    
    result: Dict[str, Any] = Field(..., description="Task result data")
    notes: Optional[str] = Field(None, max_length=1000, description="Submission notes")


class TaskProgressUpdate(BaseModel):
    """Request model for progress updates."""
    
    progress_percent: int = Field(..., ge=0, le=100)
    message: str = Field(..., max_length=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CheckpointStatus(str, Enum):
    """Status of a checkpoint."""
    PENDING = "pending"           # Worker reached checkpoint, waiting for ACK
    ACKNOWLEDGED = "acknowledged" # Publisher confirmed, worker can proceed
    REJECTED = "rejected"         # Publisher rejected, needs rework
    BYPASSED = "bypassed"         # Checkpoint skipped (simple tasks)


class Checkpoint(BaseModel):
    """A synchronization point where publisher must confirm understanding."""
    
    checkpoint_number: int = Field(..., ge=1, le=10, description="Checkpoint index (1-10)")
    target_percent: int = Field(..., ge=0, le=100, description="Expected progress at this checkpoint")
    status: CheckpointStatus = CheckpointStatus.PENDING
    
    # Understanding summary (worker must provide)
    worker_summary: Optional[str] = Field(None, description="Worker's understanding of task so far")
    
    # Publisher feedback
    publisher_response: Optional[str] = Field(None, description="Publisher's feedback/confirmation")
    requires_changes: bool = Field(False, description="Whether rework is needed")
    
    # Timestamps
    reached_at: Optional[datetime] = Field(None)
    acknowledged_at: Optional[datetime] = Field(None)
    
    # Version control - allow rollback to here
    result_snapshot: Optional[Dict[str, Any]] = Field(None, description="Snapshot of work at this checkpoint")


class UnderstandingTest(BaseModel):
    """Mandatory understanding verification before work begins."""
    
    # Worker submits their understanding
    worker_understanding: str = Field(..., min_length=10, max_length=2000, 
                                       description="Worker's summary of what needs to be built")
    
    # Worker proposes acceptance criteria
    proposed_criteria: List[str] = Field(..., min_length=1, max_length=10,
                                          description="Specific criteria to verify completion")
    
    # Publisher confirms or corrects
    publisher_confirmation: Optional[str] = Field(None, description="Publisher's confirmation or corrections")
    confirmed: bool = Field(False, description="Whether understanding is confirmed")
    
    # Created at claim time
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = Field(None)


class CheckpointAcknowledge(BaseModel):
    """Request model for publisher to acknowledge a checkpoint."""
    
    response: str = Field(..., max_length=1000, description="Feedback or confirmation")
    requires_changes: bool = Field(False, description="True if worker needs to redo")
    changes_description: Optional[str] = Field(None, max_length=1000, 
                                                description="What needs to change if rejected")


class TaskWithCheckpoints(Task):
    """Task model extended with checkpoint support."""
    
    checkpoints: List[Checkpoint] = Field(default_factory=list)
    understanding_test: Optional[UnderstandingTest] = Field(None)
    current_checkpoint: int = Field(0, description="Current checkpoint number (0 = before first)")
    
    # Task complexity metrics
    complexity_score: int = Field(1, ge=1, le=10, description="1-10 complexity rating")
    dialogue_message_count: int = Field(0, description="Number of progress messages exchanged")
    
    # Auto-splitting
    parent_task_id: Optional[str] = Field(None, description="If this is a subtask")
    subtask_ids: List[str] = Field(default_factory=list, description="Child task IDs if split")


class SubtaskDefinition(BaseModel):
    """Definition of a subtask."""
    title: str
    description: str
    reward: float
    acceptance_criteria: List[str]


class TaskSplitRequest(BaseModel):
    """Request to split a complex task into subtasks."""
    
    reason: str = Field(..., max_length=500, description="Why this task needs splitting")
    proposed_subtasks: List[SubtaskDefinition] = Field(..., min_length=2, max_length=5,
                                                        description="List of subtask definitions")
