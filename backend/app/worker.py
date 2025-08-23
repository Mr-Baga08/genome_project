# backend/app/worker.py
import asyncio
import os
import redis
from rq import Worker, Queue, Connection
from motor.motor_asyncio import AsyncIOMotorClient
from .services.task_manager import TaskManager
from .models.task import Task, TaskStatus

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'ugene_workflows')

def create_worker():
    """Create and configure RQ worker"""
    redis_client = redis.from_url(REDIS_URL)
    
    # Create MongoDB connection
    mongo_client = AsyncIOMotorClient(MONGODB_URL)
    database = mongo_client[DATABASE_NAME]
    
    # Create task manager
    task_manager = TaskManager(database, redis_client)
    
    # Create queue
    queue = Queue(connection=redis_client)
    
    return Worker([queue], connection=redis_client)

def execute_task(task_id: str):
    """Worker function to execute a single task"""
    import asyncio
    asyncio.run(execute_task_async(task_id))

async def execute_task_async(task_id: str):
    """Async worker function to execute a single task"""
    try:
        # Setup connections
        redis_client = redis.from_url(REDIS_URL)
        mongo_client = AsyncIOMotorClient(MONGODB_URL)
        database = mongo_client[DATABASE_NAME]
        
        # Create task manager
        task_manager = TaskManager(database, redis_client)
        
        # Execute the task
        await task_manager._execute_task_worker(task_id)
        
    except Exception as e:
        print(f"Worker error executing task {task_id}: {e}")
        # Log error to database
        await task_manager.update_task_status(
            task_id, 
            TaskStatus.FAILED, 
            error_logs=str(e)
        )
    finally:
        mongo_client.close()

if __name__ == '__main__':
    print("Starting UGENE workflow worker...")
    worker = create_worker()
    worker.work()
