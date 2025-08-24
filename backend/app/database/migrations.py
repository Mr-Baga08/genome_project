# backend/app/database/migrations.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

class DatabaseMigrations:
    """Database migration management"""
    
    def __init__(self, database_manager):
        self.db_manager = database_manager
        self.database = database_manager.database
    
    async def run_migrations(self):
        """Run all pending migrations"""
        migrations = [
            self._migration_001_add_workflow_templates,
            self._migration_002_add_user_preferences,
            self._migration_003_add_analysis_templates,
        ]
        
        for migration in migrations:
            try:
                await migration()
                print(f"Migration {migration.__name__} completed successfully")
            except Exception as e:
                print(f"Migration {migration.__name__} failed: {str(e)}")
    
    async def _migration_001_add_workflow_templates(self):
        """Add default workflow templates"""
        templates = [
            {
                "id": "basic_sequence_analysis",
                "name": "Basic Sequence Analysis",
                "description": "Basic sequence statistics and BLAST search",
                "category": "analysis",
                "nodes": [
                    {
                        "id": "read_sequences",
                        "type": "read_alignment",
                        "parameters": {"format": "fasta"}
                    },
                    {
                        "id": "calculate_stats",
                        "type": "statistics", 
                        "parameters": {}
                    },
                    {
                        "id": "blast_search",
                        "type": "blast_search",
                        "parameters": {"database": "nr", "evalue": 1e-5}
                    }
                ],
                "connections": [
                    {"from": "read_sequences", "to": "calculate_stats"},
                    {"from": "calculate_stats", "to": "blast_search"}
                ],
                "is_public": True,
                "created_at": datetime.utcnow()
            }
        ]
        
        for template in templates:
            await self.database.workflow_templates.insert_one(template)
    
    async def _migration_002_add_user_preferences(self):
        """Add user preferences collection"""
        await self.database.create_collection("user_preferences")
        await self.database.user_preferences.create_index([("user_id", 1)], unique=True)
    
    async def _migration_003_add_analysis_templates(self):
        """Add analysis parameter templates"""
        templates = [
            {
                "name": "blast_default",
                "type": "blast_search",
                "parameters": {
                    "database": "nr",
                    "evalue": 1e-5,
                    "max_hits": 10,
                    "word_size": 11
                }
            },
            {
                "name": "muscle_default",
                "type": "multiple_alignment", 
                "parameters": {
                    "method": "muscle",
                    "max_iterations": 16,
                    "gap_penalty": -10
                }
            }
        ]
        
        for template in templates:
            await self.database.analysis_templates.insert_one(template)