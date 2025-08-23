# backend/app/main.py
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import redis
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from pathlib import Path

from .services.task_manager import TaskManager
from .models.task import Task, TaskStatus

# Add to main.py
from .api.workflow_elements import router as elements_router


# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ugene_workflows")

app = FastAPI(
    title="UGENE Workflow API",
    description="API for managing and executing UGENE bioinformatics workflows",
    version="1.0.0"
)
app.include_router(elements_router, prefix="/api/v1", tags=["workflow-elements"])
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for database connections
mongodb_client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None
redis_client: redis.Redis = None
task_manager: TaskManager = None

# Pydantic models for API requests
class WorkflowSubmissionRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    priority: str = "medium"

class TaskListResponse(BaseModel):
    tasks: List[Task]
    total_count: int
    page: int
    size: int

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    global mongodb_client, database, redis_client, task_manager
    
    # Initialize MongoDB connection
    mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    database = mongodb_client[DATABASE_NAME]
    
    # Initialize Redis connection
    redis_client = redis.Redis.from_url(REDIS_URL)
    
    # Initialize TaskManager
    task_manager = TaskManager(database, redis_client)
    
    print("✅ Application startup complete")

@app.on_event("shutdown") 
async def shutdown_event():
    global mongodb_client, redis_client
    
    if mongodb_client:
        mongodb_client.close()
    if redis_client:
        redis_client.close()
    
    print("✅ Application shutdown complete")

# Dependency to get task manager
async def get_task_manager() -> TaskManager:
    return task_manager

# API Endpoints
@app.post("/workflows/", response_model=Dict[str, str])
async def submit_workflow(
    request: WorkflowSubmissionRequest,
    tm: TaskManager = Depends(get_task_manager)
):
    """
    Submit a new workflow for execution.
    
    This endpoint accepts a workflow definition from the frontend (nodes and connections)
    and creates a new task for processing.
    """
    try:
        workflow_definition = {
            "nodes": request.nodes,
            "connections": request.connections
        }
        
        task_id = await tm.create_task(workflow_definition, request.priority)
        
        return {
            "message": "Workflow submitted successfully",
            "task_id": task_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit workflow: {str(e)}")

@app.get("/tasks/", response_model=TaskListResponse)
async def get_all_tasks(
    page: int = 1,
    size: int = 10,
    tm: TaskManager = Depends(get_task_manager)
):
    """
    Get a paginated list of all tasks with their status and metadata.
    """
    try:
        tasks = await tm.get_all_tasks(page, size)
        
        # Get total count for pagination
        total_count = await database.tasks.count_documents({})
        
        return TaskListResponse(
            tasks=tasks,
            total_count=total_count,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tasks: {str(e)}")

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task_details(
    task_id: str,
    tm: TaskManager = Depends(get_task_manager)
):
    """
    Get detailed status, timestamps, and logs for a specific task.
    """
    try:
        task = await tm.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task: {str(e)}")

@app.get("/tasks/{task_id}/results")
async def get_task_results(
    task_id: str,
    tm: TaskManager = Depends(get_task_manager)
):
    """
    Get downloadable URLs for the output files of a completed task.
    """
    try:
        task = await tm.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Task is not completed. Current status: {task.status}"
            )
        
        # Generate download URLs for output files
        download_urls = []
        for file_path in task.output_files:
            filename = os.path.basename(file_path)
            download_url = f"/download/{task_id}/{filename}"
            download_urls.append({
                "filename": filename,
                "download_url": download_url,
                "file_path": file_path
            })
        
        return {
            "task_id": task_id,
            "status": task.status,
            "output_files": download_urls
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task results: {str(e)}")

@app.get("/download/{task_id}/{filename}")
async def download_file(
    task_id: str,
    filename: str,
    tm: TaskManager = Depends(get_task_manager)
):
    """
    Download a specific output file from a completed task.
    """
    try:
        task = await tm.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Find the requested file
        target_file = None
        for file_path in task.output_files:
            if os.path.basename(file_path) == filename:
                target_file = file_path
                break
        
        if not target_file or not os.path.exists(target_file):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=target_file,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload input files for workflows.
    """
    try:
        upload_dir = Path("/tmp/uploads")
        upload_dir.mkdir(exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            file_path = upload_dir / file.filename
            
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            uploaded_files.append({
                "filename": file.filename,
                "file_path": str(file_path),
                "size": len(content)
            })
        
        return {
            "message": "Files uploaded successfully",
            "files": uploaded_files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")

# UMAP endpoint (keeping from original implementation)
@app.post("/data/umap")
async def process_umap_data(file: UploadFile = File(...)):
    """
    Process CSV data for UMAP dimensionality reduction and clustering.
    """
    try:
        import pandas as pd
        import numpy as np
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans, DBSCAN
        import umap
        import io
        
        # Read uploaded file
        contents = await file.read()
        data = pd.read_csv(io.BytesIO(contents))
        
        # Automatically detect numeric feature columns
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_columns) < 2:
            raise HTTPException(
                status_code=400,
                detail="Dataset must have at least 2 numeric columns for UMAP analysis"
            )
        
        # Data preprocessing
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data[numeric_columns])
        
        # UMAP dimensionality reduction
        umap_reducer = umap.UMAP(
            n_neighbors=15,
            min_dist=0.1,
            n_components=2,
            random_state=42
        )
        umap_embeddings = umap_reducer.fit_transform(data_scaled)
        
        # Add UMAP coordinates to dataframe
        data["UMAP_1"] = umap_embeddings[:, 0]
        data["UMAP_2"] = umap_embeddings[:, 1]
        
        # Clustering
        kmeans = KMeans(n_clusters=3, random_state=42)
        data["Cluster_Kmeans"] = kmeans.fit_predict(data_scaled)
        
        dbscan = DBSCAN(eps=0.5, min_samples=5)
        data["Cluster_DBSCAN"] = dbscan.fit_predict(data_scaled)
        
        # Convert to JSON
        json_output = data.to_json(orient='records')
        
        return JSONResponse(content={
            "message": "UMAP analysis completed successfully",
            "data": json_output,
            "feature_columns": numeric_columns,
            "total_samples": len(data)
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"UMAP processing failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Application health check endpoint."""
    try:
        # Test database connection
        await database.command("ping")
        
        # Test Redis connection  
        redis_client.ping()
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e)
            }
        )
