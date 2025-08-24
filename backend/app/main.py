# backend/app/main.py - Updated main file
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import redis
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from pathlib import Path

# Import routers
from .api.workflow_elements import router as elements_router
from .api.sequences import router as sequences_router  
from .api.workflows import router as workflows_router

# Import services and database
from .services.workflow_engine import WorkflowEngine
from .database.database_setup import DatabaseManager
from .database.migrations import DatabaseMigrations

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ugene_workflows")

app = FastAPI(
    title="Enhanced UGENE Workflow API",
    description="Complete bioinformatics workflow platform with UGENE integration",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
database_manager: DatabaseManager = None
workflow_engine: WorkflowEngine = None
redis_client: redis.Redis = None

# Include API routers
app.include_router(elements_router, prefix="/api/v1", tags=["workflow-elements"])
app.include_router(sequences_router, prefix="/api/v1", tags=["sequences"])
app.include_router(workflows_router, prefix="/api/v1", tags=["workflows"])

@app.on_event("startup")
async def startup_event():
    global database_manager, workflow_engine, redis_client
    
    # Initialize database
    database_manager = DatabaseManager(MONGODB_URL, DATABASE_NAME)
    await database_manager.initialize_database()
    
    # Run database migrations
    migrations = DatabaseMigrations(database_manager)
    await migrations.run_migrations()
    
    # Initialize Redis
    redis_client = redis.Redis.from_url(REDIS_URL)
    
    # Initialize workflow engine
    workflow_engine = WorkflowEngine(
        database_manager.database,
        redis_client,
        logger=None  # Add proper logger
    )
    
    print("🚀 Enhanced UGENE Workflow API startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    global database_manager, redis_client
    
    if database_manager:
        await database_manager.close_connection()
    if redis_client:
        redis_client.close()
    
    print("✅ Application shutdown complete")

# Dependency providers
async def get_database_manager() -> DatabaseManager:
    return database_manager

async def get_workflow_engine() -> WorkflowEngine:
    return workflow_engine

# Health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check with service status"""
    try:
        # Check database connection
        await database_manager.database.command("ping")
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    try:
        # Check Redis connection
        redis_client.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        "services": {
            "database": db_status,
            "redis": redis_status,
            "workflow_engine": "healthy" if workflow_engine else "unhealthy"
        },
        "version": "2.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Enhanced UGENE Workflow API",
        "version": "2.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }