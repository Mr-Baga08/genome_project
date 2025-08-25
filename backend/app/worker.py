# backend/app/worker.py (Celery version)
import os
import redis # Still needed for your TaskManager, but not directly by Celery
from celery import Celery
from motor.motor_asyncio import AsyncIOMotorClient
from .services.task_manager import TaskManager
from .models.task import Task, TaskStatus

# --- Configuration ---
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'ugene_workflows')

# --- Celery Application Setup ---
# 1. Initialize Celery. The first argument is the name of the module.
#    'broker' is where tasks are sent. 'backend' is where results are stored.
app = Celery(
    'ugene_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Optional: Configure timezone. It's good practice.
# Your location is Bhubaneswar, so Asia/Kolkata is the correct timezone.
app.conf.timezone = 'Asia/Kolkata'

# --- Celery Task Definition ---
# 2. Define the task using the @app.task decorator.
#    Celery directly supports 'async def', so no need for wrappers.
@app.task(name="execute_ugene_task")
async def execute_task(task_id: str):
    """Async Celery task to execute a single workflow task"""
    
    mongo_client = None  # Define here to ensure it's available in finally
    try:
        # Setup connections within the task for process safety
        redis_client = redis.from_url(REDIS_URL)
        mongo_client = AsyncIOMotorClient(MONGODB_URL)
        database = mongo_client[DATABASE_NAME]
        
        # Create task manager
        task_manager = TaskManager(database, redis_client)
        
        # Execute the task (your core logic remains the same)
        await task_manager._execute_task_worker(task_id)
        
    except Exception as e:
        print(f"Celery worker error executing task {task_id}: {e}")
        # Log error to database. Note: you need a new TaskManager instance
        # here or handle the connection closing carefully.
        # For simplicity, let's re-create what's needed for error logging.
        if not mongo_client:
            mongo_client = AsyncIOMotorClient(MONGODB_URL)
            database = mongo_client[DATABASE_NAME]
        
        error_task_manager = TaskManager(database, None) # Redis not needed for status update
        await error_task_manager.update_task_status(
            task_id, 
            TaskStatus.FAILED, 
            error_logs=str(e)
        )
        # Re-raise the exception so Celery knows the task failed
        raise
    finally:
        if mongo_client:
            mongo_client.close()

# 3. The RQ-specific functions like create_worker() and the
#    if __name__ == '__main__': block are no longer needed and should be removed.