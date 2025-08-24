
# backend/app/models/enhanced_models.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
import uuid

class SequenceType(str, Enum):
    DNA = "DNA"
    RNA = "RNA"
    PROTEIN = "PROTEIN"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StrandType(str, Enum):
    POSITIVE = "+"
    NEGATIVE = "-"
    UNKNOWN = "."

# Enhanced Sequence Model
class SequenceData(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    sequence: str
    sequence_type: SequenceType
    organism_id: Optional[int] = None
    user_id: Optional[str] = None
    length: Optional[int] = None
    gc_content: Optional[float] = None
    checksum: Optional[str] = None
    source: Optional[str] = None
    accession_number: Optional[str] = None
    is_public: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('length', always=True)
    def calculate_length(cls, v, values):
        if 'sequence' in values:
            return len(values['sequence'])
        return v
    
    @validator('gc_content', always=True)
    def calculate_gc_content(cls, v, values):
        if 'sequence' in values and values.get('sequence_type') in ['DNA', 'RNA']:
            sequence = values['sequence'].upper()
            gc_count = sequence.count('G') + sequence.count('C')
            return (gc_count / len(sequence)) * 100 if sequence else 0.0
        return v

# Annotation Model
class Annotation(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_id: str
    feature_type: str
    start_position: int
    end_position: int
    strand: StrandType = StrandType.UNKNOWN
    score: Optional[float] = None
    phase: Optional[int] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
    method: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('start_position', 'end_position')
    def validate_positions(cls, v):
        if v <= 0:
            raise ValueError('Positions must be positive')
        return v
    
    @validator('end_position')
    def validate_position_range(cls, v, values):
        if 'start_position' in values and v < values['start_position']:
            raise ValueError('End position must be >= start position')
        return v

# Enhanced Task Model
class EnhancedTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    workflow_definition: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    
    # Execution details
    commands: List[str] = Field(default_factory=list)
    input_files: List[str] = Field(default_factory=list)
    output_files: List[str] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results and logs
    results: Optional[Dict[str, Any]] = None
    progress: int = 0
    error_message: Optional[str] = None
    execution_logs: List[str] = Field(default_factory=list)
    
    # Resource usage
    cpu_time_seconds: Optional[int] = None
    memory_used_mb: Optional[int] = None
    
    # Parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)

# Workflow Definition Model
class WorkflowDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    version: str = "1.0"
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Workflow structure
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_public: bool = False

# Analysis Result Model
class AnalysisResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    analysis_type: str
    results: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# User Model
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    full_name: Optional[str] = None
    organization: Optional[str] = None
    is_active: bool = True
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

# Request/Response Models
class WorkflowExecutionRequest(BaseModel):
    workflow_definition: WorkflowDefinition
    input_data: Optional[Dict[str, Any]] = None
    priority: str = "medium"

class TaskListResponse(BaseModel):
    tasks: List[EnhancedTask]
    total_count: int
    page: int
    size: int

class SequenceAnalysisRequest(BaseModel):
    sequence_ids: List[str]
    analysis_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class BlastSearchRequest(BaseModel):
    sequences: List[str]
    database: str = "nr"
    evalue: float = 1e-5
    max_hits: int = 10
    word_size: Optional[int] = None

class MultipleAlignmentRequest(BaseModel):
    sequences: List[SequenceData]
    method: str = "muscle"
    parameters: Dict[str, Any] = Field(default_factory=dict)


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