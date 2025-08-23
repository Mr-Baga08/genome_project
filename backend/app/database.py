# backend/app/database.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import os

class Database:
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

db = Database()

async def connect_to_mongo():
    """Create database connection"""
    print("Connecting to MongoDB...")
    
    mongodb_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
    database_name = os.getenv('DATABASE_NAME', 'ugene_workflows')
    
    db.client = AsyncIOMotorClient(mongodb_url)
    db.database = db.client[database_name]
    
    # Test connection
    try:
        await db.client.admin.command('ping')
        print(f"✅ Connected to MongoDB: {database_name}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise

    return db.database

async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        print("✅ Disconnected from MongoDB")

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return db.database

# Database initialization
async def init_database():
    """Initialize database with indexes and collections"""
    database = await get_database()
    
    # Create indexes for tasks collection
    tasks_collection = database.tasks
    
    # Index for efficient task queries
    await tasks_collection.create_index("task_id", unique=True)
    await tasks_collection.create_index("status")
    await tasks_collection.create_index("timestamps.created")
    await tasks_collection.create_index("priority")
    
    print("✅ Database indexes created")

