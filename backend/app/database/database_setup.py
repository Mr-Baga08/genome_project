# backend/app/database/database_setup.py
import motor.motor_asyncio
from typing import Optional
import os

class DatabaseManager:
    """Enhanced database manager with indexing and optimization"""
    
    def __init__(self, mongodb_url: str, database_name: str):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        self.database = self.client[database_name]
    
    async def initialize_database(self):
        """Initialize database with indexes and collections"""
        await self._create_indexes()
        await self._create_collections()
    
    async def _create_collections(self):
        """Create necessary collections"""
        collections = [
            'sequences',
            'annotations', 
            'tasks',
            'users',
            'workflows',
            'analysis_results',
            'workflow_executions'
        ]
        
        existing_collections = await self.database.list_collection_names()
        
        for collection in collections:
            if collection not in existing_collections:
                await self.database.create_collection(collection)
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        
        # Sequences collection indexes
        await self.database.sequences.create_index([("user_id", 1), ("sequence_type", 1)])
        await self.database.sequences.create_index([("organism_id", 1)])
        await self.database.sequences.create_index([("length", 1)])
        await self.database.sequences.create_index([("gc_content", 1)])
        await self.database.sequences.create_index([("checksum", 1)])
        await self.database.sequences.create_index([("created_at", -1)])
        await self.database.sequences.create_index([("is_public", 1)])
        
        # Annotations collection indexes
        await self.database.annotations.create_index([("sequence_id", 1)])
        await self.database.annotations.create_index([("feature_type", 1)])
        await self.database.annotations.create_index([("start_position", 1), ("end_position", 1)])
        await self.database.annotations.create_index([("sequence_id", 1), ("start_position", 1)])
        
        # Tasks collection indexes
        await self.database.tasks.create_index([("user_id", 1), ("status", 1)])
        await self.database.tasks.create_index([("status", 1)])
        await self.database.tasks.create_index([("priority", -1), ("created_at", 1)])
        await self.database.tasks.create_index([("created_at", -1)])
        await self.database.tasks.create_index([("task_id", 1)], unique=True)
        
        # Users collection indexes
        await self.database.users.create_index([("username", 1)], unique=True)
        await self.database.users.create_index([("email", 1)], unique=True)
        await self.database.users.create_index([("is_active", 1)])
        
        # Workflows collection indexes
        await self.database.workflows.create_index([("author", 1)])
        await self.database.workflows.create_index([("tags", 1)])
        await self.database.workflows.create_index([("is_public", 1)])
        await self.database.workflows.create_index([("created_at", -1)])
        
        # Analysis results collection indexes
        await self.database.analysis_results.create_index([("task_id", 1)])
        await self.database.analysis_results.create_index([("analysis_type", 1)])
        await self.database.analysis_results.create_index([("created_at", -1)])
    
    async def get_collection(self, collection_name: str):
        """Get database collection"""
        return self.database[collection_name]
    
    async def close_connection(self):
        """Close database connection"""
        self.client.close()
