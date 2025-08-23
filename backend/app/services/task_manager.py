# backend/app/services/task_manager.py
import uuid
import asyncio
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from rq import Queue
from redis import Redis
from datetime import datetime

from ..models.task import Task, TaskStatus
from ..services.ugene_runner import UgeneRunner

class TaskManager:
    def __init__(self, db: AsyncIOMotorDatabase, redis_client: Redis):
        self.db = db
        self.tasks_collection = db.tasks
        self.redis_client = redis_client
        self.task_queue = Queue(connection=redis_client)
        self.ugene_runner = UgeneRunner()

    async def create_task(self, workflow_definition: dict, priority: str = "medium") -> str:
        """Create a new task from workflow definition"""
        task_id = str(uuid.uuid4())
        
        # Convert workflow to UGENE commands
        commands = self._workflow_to_commands(workflow_definition)
        
        task = Task(
            task_id=task_id,
            workflow_definition=workflow_definition,
            commands=commands,
            priority=priority,
            timestamps={
                "created": datetime.utcnow(),
                "started": None,
                "completed": None
            }
        )
        
        # Save to MongoDB
        await self.tasks_collection.insert_one(task.dict())
        
        # Add to Redis queue for processing
        self.task_queue.enqueue(
            self._execute_task_worker,
            task_id,
            job_timeout='30m',
            job_id=task_id
        )
        
        return task_id

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID"""
        task_data = await self.tasks_collection.find_one({"task_id": task_id})
        if task_data:
            return Task(**task_data)
        return None

    async def get_all_tasks(self, page: int = 1, size: int = 10) -> List[Task]:
        """Get paginated list of all tasks"""
        skip = (page - 1) * size
        cursor = self.tasks_collection.find().skip(skip).limit(size).sort("timestamps.created", -1)
        tasks = []
        async for task_data in cursor:
            tasks.append(Task(**task_data))
        return tasks

    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               logs: Optional[str] = None, error_logs: Optional[str] = None,
                               output_files: List[str] = None):
        """Update task status and metadata"""
        update_data = {"status": status}
        
        if logs:
            update_data["logs"] = logs
        if error_logs:
            update_data["error_logs"] = error_logs
        if output_files:
            update_data["output_files"] = output_files
            
        # Update timestamps
        if status == TaskStatus.RUNNING:
            update_data["timestamps.started"] = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            update_data["timestamps.completed"] = datetime.utcnow()
            
        await self.tasks_collection.update_one(
            {"task_id": task_id}, 
            {"$set": update_data}
        )

    def _workflow_to_commands(self, workflow_definition: dict) -> List[str]:
        """Convert workflow definition to UGENE commands"""
        commands = []
        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", [])
        
        # Process each node and generate appropriate UGENE command
        for node in nodes:
            node_type = node.get("type", "")
            node_name = node.get("name", "")
            
            if "Read FASTQ" in node_name:
                commands.append(f"ugene --task=read-sequence --in={node.get('input_file', '')}")
            elif "Align with" in node_name:
                aligner = node_name.split("Align with ")[1].lower()
                commands.append(f"ugene --task=align-{aligner} --in=input.fasta --out=output.aln")
            elif "Build Tree" in node_name:
                tree_method = node_name.split("Build Tree with ")[1].lower().replace(" ", "-")
                commands.append(f"ugene --task=build-tree-{tree_method} --in=alignment.aln --out=tree.nwk")
            # Add more node type mappings as needed
            
        return commands

    async def _execute_task_worker(self, task_id: str):
        """Worker function executed by Redis Queue"""
        try:
            # Update status to running
            await self.update_task_status(task_id, TaskStatus.RUNNING)
            
            # Get task details
            task = await self.get_task(task_id)
            if not task:
                raise Exception(f"Task {task_id} not found")
            
            # Execute task using UgeneRunner
            result = await self.ugene_runner.execute_task(task)
            
            # Update task with results
            if result.success:
                await self.update_task_status(
                    task_id, 
                    TaskStatus.COMPLETED,
                    logs=result.stdout,
                    output_files=result.output_files
                )
            else:
                await self.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    logs=result.stdout,
                    error_logs=result.stderr
                )
                
        except Exception as e:
            await self.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_logs=str(e)
            )

