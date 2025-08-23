# backend/app/models/task.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.QUEUED
    workflow_definition: Dict[str, Any]
    commands: List[str] = []
    input_files: List[str] = []
    output_files: List[str] = []
    logs: Optional[str] = None
    error_logs: Optional[str] = None
    timestamps: Dict[str, Optional[datetime]] = Field(default_factory=lambda: {
        "created": datetime.utcnow(),
        "started": None,
        "completed": None
    })
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
