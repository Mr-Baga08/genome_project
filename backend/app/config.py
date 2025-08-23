# backend/app/config.py
import os
from pathlib import Path
from typing import List

class Settings:
    # Database
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ugene_workflows")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # File Storage
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    UGENE_WORKDIR: Path = Path(os.getenv("UGENE_WORKDIR", "/tmp/ugene_workdir"))
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "UGENE Workflow API"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
    ]
    
    # UGENE
    UGENE_IMAGE: str = os.getenv("UGENE_IMAGE", "ugene_sdk_docker_image")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    def __init__(self):
        # Ensure directories exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.UGENE_WORKDIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
