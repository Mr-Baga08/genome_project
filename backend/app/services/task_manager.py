# backend/app/services/task_manager.py
import uuid
import asyncio
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

# --- Key Change: Import the Celery task ---
# We no longer import RQ. Instead, we import the task function we defined in our worker.
# from ..worker import execute_task

from ..models.task import Task, TaskStatus
from ..services.ugene_runner import UgeneRunner

class TaskManager:
    # --- Key Change: __init__ no longer needs redis_client ---
    # Its responsibility is now focused on managing tasks in the database.
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.tasks_collection = db.tasks
        self.ugene_runner = UgeneRunner()

    async def create_task(self, workflow_definition: dict, priority: str = "medium") -> str:
        """Create a new task and submit it to the Celery worker"""
        task_id = str(uuid.uuid4())
        
        # This logic remains the same
        commands = self._workflow_to_commands(workflow_definition)
        
        task = Task(
            task_id=task_id,
            workflow_definition=workflow_definition,
            commands=commands,
            priority=priority,
            timestamps={
                "created": datetime.now(), # Using timezone-aware now() is often better
                "started": None,
                "completed": None
            }
        )
        
        # Save to MongoDB (remains the same)
        await self.tasks_collection.insert_one(task.dict())
        
        # --- Key Change: Enqueue task using Celery ---
        # Instead of using rq's queue.enqueue, we call .delay() on our imported task.
        # This sends the task to the Redis broker for a Celery worker to pick up.
        execute_task.delay(task_id)
        
        return task_id

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID (No changes needed)"""
        task_data = await self.tasks_collection.find_one({"task_id": task_id})
        if task_data:
            return Task(**task_data)
        return None

    async def get_all_tasks(self, page: int = 1, size: int = 10) -> List[Task]:
        """Get paginated list of all tasks (No changes needed)"""
        skip = (page - 1) * size
        cursor = self.tasks_collection.find().skip(skip).limit(size).sort("timestamps.created", -1)
        tasks = []
        async for task_data in cursor:
            tasks.append(Task(**task_data))
        return tasks

    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               logs: Optional[str] = None, error_logs: Optional[str] = None,
                               output_files: List[str] = None):
        """Update task status and metadata (No changes needed)"""
        update_data = {"status": status}
        
        if logs is not None:
            update_data["logs"] = logs
        if error_logs is not None:
            update_data["error_logs"] = error_logs
        if output_files is not None:
            update_data["output_files"] = output_files
            
        if status == TaskStatus.RUNNING:
            update_data["timestamps.started"] = datetime.now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            update_data["timestamps.completed"] = datetime.now()
            
        await self.tasks_collection.update_one(
            {"task_id": task_id}, 
            {"$set": update_data}
        )

    def _workflow_to_commands(self, workflow_definition: dict) -> List[str]:
        """Convert workflow definition to UGENE commands (No changes needed)"""
        commands = []
        nodes = workflow_definition.get("nodes", [])
        
        for node in nodes:
            node_name = node.get("name", "")
            
            if "Read FASTQ" in node_name:
                commands.append(f"ugene --task=read-sequence --in={node.get('input_file', '')}")
            elif "Align with" in node_name:
                aligner = node_name.split("Align with ")[1].lower()
                commands.append(f"ugene --task=align-{aligner} --in=input.fasta --out=output.aln")
            elif "Build Tree" in node_name:
                tree_method = node_name.split("Build Tree with ")[1].lower().replace(" ", "-")
                commands.append(f"ugene --task=build-tree-{tree_method} --in=alignment.aln --out=tree.nwk")
            
        return commands

    # --- Key Change: The worker execution logic is REMOVED ---
    # The _execute_task_worker method is no longer needed here.
    # Its logic has been moved to the Celery task in 'app/worker.py'.