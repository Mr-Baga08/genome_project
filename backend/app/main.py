# backend/app/main.py - FIXED VERSION
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances (initialized in lifespan)
db_manager = None
cache_manager = None
external_tools = None
connection_manager = None
analysis_tracker = None
file_handler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events with proper error handling"""
    logger.info("🚀 Starting UGENE Web Platform...")
    
    # Initialize global services
    global db_manager, cache_manager, external_tools, connection_manager, analysis_tracker, file_handler
    
    try:
        # Initialize database (optional - graceful degradation)
        try:
            from .database.database_setup import DatabaseManager
            mongodb_url = os.getenv('MONGODB_URL', 'mongodb://mongodb:27017')
            database_name = os.getenv('DATABASE_NAME', 'ugene_bioinformatics')
            
            db_manager = DatabaseManager(mongodb_url, database_name)
            await db_manager.initialize_database()
            logger.info("✅ Database connected successfully")
            
            # Store in app state
            app.state.db_manager = db_manager
            
        except Exception as e:
            logger.warning(f"⚠️  Database initialization failed: {str(e)}")
            logger.warning("🔄 Continuing without database (using mock data)")
            app.state.db_manager = None
        
        # Initialize cache (optional - graceful degradation)
        try:
            from .services.caching_manager import BioinformaticsCacheManager
            redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
            cache_manager = BioinformaticsCacheManager(redis_url)
            logger.info("✅ Cache manager initialized")
            app.state.cache_manager = cache_manager
            
        except Exception as e:
            logger.warning(f"⚠️  Cache initialization failed: {str(e)}")
            logger.warning("🔄 Continuing without cache")
            app.state.cache_manager = None
        
        # Initialize external tools (with lazy Docker loading)
        try:
            from .services.external_tool_manager import ExternalToolManager
            external_tools = ExternalToolManager()
            logger.info("✅ External tools manager initialized")
            app.state.external_tools = external_tools
            
        except Exception as e:
            logger.warning(f"⚠️  External tools initialization failed: {str(e)}")
            app.state.external_tools = None
        
        # Initialize WebSocket manager (optional)
        try:
            from .websockets.connection_manager import ConnectionManager, AnalysisProgressTracker
            connection_manager = ConnectionManager()
            analysis_tracker = AnalysisProgressTracker(connection_manager)
            logger.info("✅ WebSocket manager initialized")
            app.state.connection_manager = connection_manager
            app.state.analysis_tracker = analysis_tracker
            
        except Exception as e:
            logger.warning(f"⚠️  WebSocket initialization failed: {str(e)}")
            app.state.connection_manager = None
            app.state.analysis_tracker = None
        
        # Initialize file handler
        try:
            from .utils.file_handlers import FileHandler
            file_handler = FileHandler()
            logger.info("✅ File handler initialized")
            app.state.file_handler = file_handler
            
        except Exception as e:
            logger.warning(f"⚠️  File handler initialization failed: {str(e)}")
            app.state.file_handler = None
        
        logger.info("✅ Application startup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Critical startup error: {str(e)}")
        # Continue anyway for development
        yield
    
    finally:
        # Cleanup on shutdown
        logger.info("🔄 Shutting down services...")
        
        if db_manager:
            try:
                await db_manager.close_connection()
                logger.info("✅ Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database: {str(e)}")
        
        logger.info("✅ Shutdown completed")

# Create FastAPI application
app = FastAPI(
    title="UGENE Web Platform API",
    description="Modern web-based bioinformatics analysis platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(','),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Basic endpoints that work without external dependencies
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "UGENE Web Platform API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {}
    }
    
    # Check database connection
    if hasattr(app.state, 'db_manager') and app.state.db_manager:
        try:
            await app.state.db_manager.database.command("ping")
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["database"] = "not_available"
        health_status["status"] = "degraded"
    
    # Check cache connection
    if hasattr(app.state, 'cache_manager') and app.state.cache_manager:
        try:
            cache_stats = await app.state.cache_manager.get_cache_stats()
            health_status["services"]["cache"] = "healthy"
            health_status["cache_hit_rate"] = cache_stats.get("hit_rate", 0)
        except Exception as e:
            health_status["services"]["cache"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["cache"] = "not_available"
    
    # Check external tools (Docker)
    if hasattr(app.state, 'external_tools') and app.state.external_tools:
        if app.state.external_tools._is_docker_available():
            health_status["services"]["docker"] = "healthy"
        else:
            health_status["services"]["docker"] = "unavailable"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["docker"] = "not_initialized"
    
    # Check WebSocket connections
    if hasattr(app.state, 'connection_manager') and app.state.connection_manager:
        stats = app.state.connection_manager.get_stats()
        health_status["services"]["websocket"] = "healthy"
        health_status["active_connections"] = stats["active_connections"]
    else:
        health_status["services"]["websocket"] = "not_available"
    
    return health_status

@app.get("/info", tags=["System"])
async def system_info():
    """Get system information"""
    info = {
        "application": {
            "name": "UGENE Web Platform",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "startup_time": datetime.utcnow().isoformat()
        },
        "services": {
            "database": "available" if (hasattr(app.state, 'db_manager') and app.state.db_manager) else "unavailable",
            "cache": "available" if (hasattr(app.state, 'cache_manager') and app.state.cache_manager) else "unavailable",
            "external_tools": "available" if (hasattr(app.state, 'external_tools') and app.state.external_tools) else "unavailable",
            "websocket": "available" if (hasattr(app.state, 'connection_manager') and app.state.connection_manager) else "unavailable"
        }
    }
    
    return info

# Include API routers with error handling
try:
    from .api.sequences import router as sequences_router
    app.include_router(sequences_router, prefix="/api/v1", tags=["Sequences"])
    logger.info("✅ Sequences API router loaded")
except Exception as e:
    logger.warning(f"⚠️  Failed to load sequences router: {str(e)}")

try:
    from .api.workflow_elements import router as workflow_router
    app.include_router(workflow_router, prefix="/api/v1", tags=["Workflows"])
    logger.info("✅ Workflow API router loaded")
except Exception as e:
    logger.warning(f"⚠️  Failed to load workflow router: {str(e)}")

try:
    from .api.workflows import router as workflows_api_router
    app.include_router(workflows_api_router, prefix="/api/v1", tags=["Workflow Management"])
    logger.info("✅ Workflows API router loaded")
except Exception as e:
    logger.warning(f"⚠️  Failed to load workflows router: {str(e)}")

# Enhanced API endpoints (load conditionally)
try:
    from .api.enhanced_endpoints import router as enhanced_api_router
    app.include_router(enhanced_api_router, tags=["Enhanced API"])
    logger.info("✅ Enhanced API router loaded")
except Exception as e:
    logger.warning(f"⚠️  Failed to load enhanced API router: {str(e)}")

# Basic analysis endpoints that work without Docker
@app.post("/api/v1/analysis/blast-search", tags=["Analysis"])
async def run_basic_blast_search(request: dict):
    """Basic BLAST search endpoint"""
    try:
        if hasattr(app.state, 'external_tools') and app.state.external_tools:
            # Use the external tools service
            result = await app.state.external_tools.execute_blast_search(
                sequence=request.get("sequences", [""])[0],
                database=request.get("database", "nr"),
                parameters={
                    "evalue": request.get("evalue", 1e-5),
                    "max_hits": request.get("max_hits", 10)
                }
            )
            return result
        else:
            # Return mock result
            return {
                "results": [{
                    "query_id": "query_1",
                    "hits": [{
                        "accession": "MOCK_001",
                        "description": "Mock BLAST hit for development",
                        "score": 85.5,
                        "evalue": 1e-7,
                        "identity": 0.85
                    }]
                }],
                "database": request.get("database", "nr"),
                "method": "mock",
                "message": "Mock BLAST result - Docker not available"
            }
    except Exception as e:
        logger.error(f"BLAST search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analysis/multiple-alignment", tags=["Analysis"])
async def run_basic_alignment(request: dict):
    """Basic multiple alignment endpoint"""
    try:
        sequences = [seq.get("sequence", "") for seq in request.get("sequences", [])]
        method = request.get("method", "muscle")
        
        if hasattr(app.state, 'external_tools') and app.state.external_tools:
            result = await app.state.external_tools.execute_multiple_alignment(
                sequences=sequences,
                tool=method,
                parameters=request.get("parameters", {})
            )
            return result
        else:
            # Return mock alignment
            aligned_sequences = []
            max_len = max(len(seq) for seq in sequences) if sequences else 0
            
            for i, seq in enumerate(sequences):
                padded_seq = seq.ljust(max_len, '-')
                aligned_sequences.append({
                    "id": f"seq_{i}",
                    "sequence": padded_seq,
                    "length": len(padded_seq)
                })
            
            return {
                "aligned_sequences": aligned_sequences,
                "alignment_statistics": {
                    "alignment_length": max_len,
                    "num_sequences": len(sequences),
                    "conservation_percentage": 75.0,
                    "gap_percentage": 15.0
                },
                "tool": f"{method} (mock)",
                "method": "mock",
                "message": "Mock alignment result - Docker not available"
            }
    except Exception as e:
        logger.error(f"Multiple alignment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint with error handling
@app.websocket("/ws")
async def websocket_connection(websocket: WebSocket):
    """WebSocket endpoint with graceful degradation"""
    try:
        if hasattr(app.state, 'connection_manager') and app.state.connection_manager:
            from .websockets.connection_manager import websocket_endpoint
            await websocket_endpoint(websocket, app.state.connection_manager)
        else:
            # Basic WebSocket handling without connection manager
            await websocket.accept()
            try:
                while True:
                    data = await websocket.receive_text()
                    # Echo back with timestamp
                    response = {
                        "type": "echo",
                        "message": f"Received: {data}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "WebSocket service limited - connection manager not available"
                    }
                    await websocket.send_text(str(response))
            except WebSocketDisconnect:
                pass
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    logger.error(f"HTTP {exc.status_code} error on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unhandled errors"""
    logger.error(f"Unhandled exception on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url),
            "message": "An unexpected error occurred. Check logs for details."
        }
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = datetime.utcnow()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    # Log request (only log non-health check requests to reduce noise)
    if not request.url.path.endswith('/health'):
        logger.info(
            f"{request.method} {request.url.path} "
            f"- {response.status_code} "
            f"- {process_time:.3f}s"
        )
    
    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Basic mock endpoints for development
@app.get("/api/v1/sequences", tags=["Sequences"])
async def list_sequences_basic():
    """Basic sequence listing endpoint"""
    try:
        if hasattr(app.state, 'db_manager') and app.state.db_manager:
            # Use actual database
            sequences_collection = await app.state.db_manager.get_collection("sequences")
            sequences = await sequences_collection.find({}).limit(20).to_list(20)
            return sequences
        else:
            # Return mock sequences
            mock_sequences = [
                {
                    "id": "seq_1",
                    "name": "Sample DNA Sequence",
                    "sequence": "ATGAAACGCATTAGCACCACCATT",
                    "sequence_type": "DNA",
                    "length": 24,
                    "gc_content": 41.7,
                    "description": "Mock sequence for development"
                },
                {
                    "id": "seq_2", 
                    "name": "Sample Protein Sequence",
                    "sequence": "MKRLATTPLTTTPSPLTTSKTNTK",
                    "sequence_type": "PROTEIN",
                    "length": 23,
                    "description": "Mock protein sequence"
                }
            ]
            return mock_sequences
    except Exception as e:
        logger.error(f"Failed to list sequences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/sequences/create", tags=["Sequences"])
async def create_sequence_basic(request: dict):
    """Basic sequence creation endpoint"""
    try:
        # Validate required fields
        if not request.get("name") or not request.get("sequence"):
            raise HTTPException(status_code=400, detail="Name and sequence are required")
        
        sequence_data = {
            "id": f"seq_{int(datetime.now().timestamp())}",
            "name": request["name"],
            "sequence": request["sequence"].upper(),
            "sequence_type": request.get("sequence_type", "DNA"),
            "length": len(request["sequence"]),
            "description": request.get("description", ""),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Calculate GC content for nucleotide sequences
        if sequence_data["sequence_type"] in ["DNA", "RNA"]:
            seq = sequence_data["sequence"]
            gc_count = seq.count('G') + seq.count('C')
            sequence_data["gc_content"] = (gc_count / len(seq)) * 100 if seq else 0
        
        if hasattr(app.state, 'db_manager') and app.state.db_manager:
            # Store in database
            sequences_collection = await app.state.db_manager.get_collection("sequences")
            result = await sequences_collection.insert_one(sequence_data)
            sequence_data["_id"] = str(result.inserted_id)
        
        logger.info(f"✅ Created sequence: {sequence_data['name']}")
        return sequence_data
        
    except Exception as e:
        logger.error(f"Failed to create sequence: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Workflow elements endpoint
@app.get("/api/v1/workflow/elements", tags=["Workflows"])
async def get_workflow_elements():
    """Get available workflow elements"""
    elements = {
        "Input/Output": [
            {
                "name": "read_fasta",
                "display_name": "Read FASTA File",
                "description": "Read sequences from FASTA format file",
                "input_ports": [],
                "output_ports": ["sequences"],
                "available": True
            },
            {
                "name": "write_fasta",
                "display_name": "Write FASTA File", 
                "description": "Write sequences to FASTA format file",
                "input_ports": ["sequences"],
                "output_ports": ["file"],
                "available": True
            }
        ],
        "Analysis Tools": [
            {
                "name": "blast_search",
                "display_name": "BLAST Search",
                "description": "Perform BLAST sequence similarity search",
                "input_ports": ["sequences"],
                "output_ports": ["results"],
                "available": True
            },
            {
                "name": "multiple_alignment",
                "display_name": "Multiple Alignment",
                "description": "Perform multiple sequence alignment",
                "input_ports": ["sequences"], 
                "output_ports": ["alignment"],
                "available": True
            },
            {
                "name": "phylogenetic_tree",
                "display_name": "Phylogenetic Tree",
                "description": "Build phylogenetic tree from alignment",
                "input_ports": ["alignment"],
                "output_ports": ["tree"],
                "available": True
            },
            {
                "name": "gene_prediction",
                "display_name": "Gene Prediction",
                "description": "Predict genes in genomic sequences",
                "input_ports": ["sequences"],
                "output_ports": ["genes"],
                "available": True
            }
        ]
    }
    
    # Add availability status based on Docker
    docker_available = False
    if hasattr(app.state, 'external_tools') and app.state.external_tools:
        docker_available = app.state.external_tools._is_docker_available()
    
    # Update availability status for all tools
    for category in elements.values():
        for element in category:
            if element.get("available") is not None:
                element["docker_available"] = docker_available
                if not docker_available:
                    element["note"] = "Running in mock mode - Docker not available"
    
    return elements

# File upload endpoints
@app.post("/api/v1/files/upload-fasta", tags=["Files"])
async def upload_fasta_basic(file: UploadFile = File(...)):
    """Basic FASTA file upload endpoint"""
    try:
        # Read file content
        file_content = await file.read()
        content_str = file_content.decode('utf-8')
        
        # Parse FASTA content
        sequences = []
        current_header = None
        current_sequence = []
        
        for line in content_str.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('>'):
                # Save previous sequence
                if current_header is not None:
                    sequences.append({
                        'name': current_header.split()[0],
                        'description': ' '.join(current_header.split()[1:]) if len(current_header.split()) > 1 else '',
                        'sequence': ''.join(current_sequence),
                        'length': len(''.join(current_sequence))
                    })
                
                # Start new sequence
                current_header = line[1:]
                current_sequence = []
            else:
                current_sequence.append(line)
        
        # Don't forget the last sequence
        if current_header is not None:
            sequences.append({
                'name': current_header.split()[0],
                'description': ' '.join(current_header.split()[1:]) if len(current_header.split()) > 1 else '',
                'sequence': ''.join(current_sequence),
                'length': len(''.join(current_sequence))
            })
        
        return {
            "filename": file.filename,
            "sequence_count": len(sequences),
            "sequences": sequences[:10],  # Return first 10 for preview
            "total_length": sum(seq["length"] for seq in sequences)
        }
        
    except Exception as e:
        logger.error(f"FASTA upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to parse FASTA file: {str(e)}")

@app.post("/upload", tags=["Files"])
async def upload_files_root(files: List[UploadFile] = File(...)):
    """Root upload endpoint for frontend compatibility"""
    return await upload_files_basic(files)

@app.post("/api/v1/upload", tags=["Files"])
async def upload_files_basic(files: List[UploadFile] = File(...)):
    """General file upload endpoint"""
    try:
        results = []
        for file in files:
            # Basic file validation
            if file.size > 100 * 1024 * 1024:  # 100MB limit
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "File too large"
                })
                continue
            
            # Process file based on extension
            file_extension = Path(file.filename).suffix.lower()
            if file_extension in ['.fasta', '.fa', '.fas']:
                # Handle FASTA files
                content = await file.read()
                content_str = content.decode('utf-8')
                
                # Basic FASTA parsing
                sequence_count = content_str.count('>')
                
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "file_type": "FASTA",
                    "sequence_count": sequence_count,
                    "size": len(content)
                })
            else:
                # Handle other files
                content = await file.read()
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "file_type": "General",
                    "size": len(content)
                })
        
        return {
            "uploaded_files": results,
            "total_files": len(files),
            "successful_uploads": sum(1 for r in results if r["success"])
        }
        
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Cache management endpoints
@app.get("/api/v1/cache/stats", tags=["Cache"])
async def get_cache_stats_basic():
    """Get cache statistics"""
    try:
        if hasattr(app.state, 'cache_manager') and app.state.cache_manager:
            return await app.state.cache_manager.get_cache_stats()
        else:
            return {
                "status": "unavailable",
                "message": "Cache service not available",
                "hit_rate": 0,
                "total_hits": 0,
                "total_misses": 0
            }
    except Exception as e:
        logger.error(f"Cache stats failed: {str(e)}")
        return {"error": str(e)}

# Development-friendly endpoints
@app.get("/api/v1/status", tags=["System"])
async def get_service_status():
    """Get detailed service status for development"""
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "services": {
            "database": {
                "available": hasattr(app.state, 'db_manager') and app.state.db_manager is not None,
                "type": "MongoDB"
            },
            "cache": {
                "available": hasattr(app.state, 'cache_manager') and app.state.cache_manager is not None,
                "type": "Redis"
            },
            "external_tools": {
                "available": hasattr(app.state, 'external_tools') and app.state.external_tools is not None,
                "docker_status": "unknown"
            },
            "websocket": {
                "available": hasattr(app.state, 'connection_manager') and app.state.connection_manager is not None
            }
        }
    }
    
    # Check Docker status if external tools are available
    if status["services"]["external_tools"]["available"]:
        try:
            docker_available = app.state.external_tools._is_docker_available()
            status["services"]["external_tools"]["docker_status"] = "available" if docker_available else "unavailable"
            status["services"]["external_tools"]["docker_error"] = None if docker_available else "Docker daemon not accessible"
        except Exception as e:
            status["services"]["external_tools"]["docker_status"] = "error"
            status["services"]["external_tools"]["docker_error"] = str(e)
    
# Missing endpoints that frontend expects
@app.get("/api/v1/pipelines", tags=["Pipelines"])
async def list_pipelines():
    """List available pipelines"""
    mock_pipelines = [
        {
            "id": "pipeline_1",
            "name": "Basic BLAST Analysis",
            "description": "BLAST search followed by alignment",
            "steps": ["blast_search", "multiple_alignment"],
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "pipeline_2", 
            "name": "Phylogenetic Analysis",
            "description": "Complete phylogenetic workflow",
            "steps": ["multiple_alignment", "phylogenetic_tree"],
            "created_at": datetime.utcnow().isoformat()
        }
    ]
    return mock_pipelines

@app.get("/api/v1/analysis/recent", tags=["Analysis"])
async def get_recent_analyses():
    """Get recent analysis results"""
    mock_analyses = [
        {
            "id": "analysis_1",
            "type": "blast_search",
            "status": "completed",
            "progress": 100,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        },
        {
            "id": "analysis_2",
            "type": "multiple_alignment", 
            "status": "running",
            "progress": 65,
            "started_at": datetime.utcnow().isoformat()
        }
    ]
    return mock_analyses

@app.post("/api/v1/pipelines/{pipeline_id}/execute", tags=["Pipelines"])
async def execute_pipeline(pipeline_id: str, request: dict):
    """Execute a specific pipeline"""
    return {
        "execution_id": f"exec_{int(datetime.now().timestamp())}",
        "pipeline": f"Pipeline {pipeline_id}",
        "status": "started",
        "sequence_ids": request.get("sequence_ids", [])
    }

@app.post("/api/v1/workflows/execute", tags=["Workflows"])
async def execute_workflow_endpoint(request: dict):
    """Execute workflow from designer"""
    return {
        "workflow_id": f"workflow_{int(datetime.now().timestamp())}",
        "status": "started",
        "message": "Workflow execution started"
    }

@app.get("/api/v1/workflows/{workflow_id}/status", tags=["Workflows"])
async def get_workflow_status(workflow_id: str):
    """Get workflow execution status"""
    return {
        "id": workflow_id,
        "status": "completed",
        "progress": 100,
        "results": ["Mock workflow results"]
    }

# Main execution
def main():
    """Main application entry point"""
    import uvicorn
    
    # Configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    workers = int(os.getenv("WORKERS", "1"))
    
    logger.info(f"🌐 Starting UGENE Web Platform on {host}:{port}")
    logger.info(f"🔄 Reload mode: {reload}")
    logger.info(f"📊 Workers: {workers}")
    
    uvicorn_config = {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "log_level": log_level,
        "reload": reload,
        "workers": workers if not reload else 1,
        "access_log": True,
    }
    
    uvicorn.run(**uvicorn_config)

if __name__ == "__main__":
    main()