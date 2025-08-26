# backend/app/main.py - FINAL CONSOLIDATED VERSION
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances will be initialized in the lifespan context
db_manager = None
cache_manager = None
external_tools = None
connection_manager = None
analysis_tracker = None
file_handler = None
monitoring_service = None

async def _log_security_event(request: Request, exc: HTTPException):
    """Helper function to log security-related events."""
    try:
        security_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "security_error",
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "details": exc.detail
        }
        logger.warning(f"Security event: {security_event}")
        # In production, this could also write to a dedicated audit log or service.
    except Exception as e:
        logger.error(f"Failed to log security event: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown logic using the modern lifespan context manager.
    This single function handles all initialization and cleanup.
    """
    logger.info("🚀 Starting UGENE Web Platform with enhanced features...")

    # Initialize global services within a single try block for clarity
    global db_manager, cache_manager, external_tools, connection_manager, analysis_tracker, file_handler, monitoring_service

    try:
        # --- CORE SERVICE INITIALIZATION ---
        try:
            from .database.database_setup import DatabaseManager
            db_manager = DatabaseManager(os.getenv('MONGODB_URL', 'mongodb://mongodb:27017'), os.getenv('DATABASE_NAME', 'ugene_bioinformatics'))
            await db_manager.initialize_database()
            app.state.db_manager = db_manager
            logger.info("✅ Database connected successfully")
        except Exception as e:
            logger.warning(f"⚠️  Database initialization failed: {str(e)}. Running in mock mode.")
            app.state.db_manager = None

        try:
            from .services.caching_manager import BioinformaticsCacheManager
            cache_manager = BioinformaticsCacheManager(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
            app.state.cache_manager = cache_manager
            logger.info("✅ Cache manager initialized")
        except Exception as e:
            logger.warning(f"⚠️  Cache initialization failed: {str(e)}. Continuing without cache.")
            app.state.cache_manager = None

        try:
            from .services.external_tool_manager import ExternalToolManager
            external_tools = ExternalToolManager()
            app.state.external_tools = external_tools
            logger.info("✅ External tools manager initialized")
        except Exception as e:
            logger.warning(f"⚠️  External tools initialization failed: {str(e)}.")
            app.state.external_tools = None

        try:
            from .websockets.connection_manager import ConnectionManager, AnalysisProgressTracker
            connection_manager = ConnectionManager()
            analysis_tracker = AnalysisProgressTracker(connection_manager)
            app.state.connection_manager = connection_manager
            app.state.analysis_tracker = analysis_tracker
            logger.info("✅ WebSocket manager initialized")
        except Exception as e:
            logger.warning(f"⚠️  WebSocket initialization failed: {str(e)}.")
            app.state.connection_manager = None
            app.state.analysis_tracker = None

        try:
            from .utils.file_handlers import FileHandler
            file_handler = FileHandler()
            app.state.file_handler = file_handler
            logger.info("✅ File handler initialized")
        except Exception as e:
            logger.warning(f"⚠️  File handler initialization failed: {str(e)}.")
            app.state.file_handler = None

        # --- ENHANCED SERVICE INITIALIZATION (from former startup event) ---
        try:
            from .security.permissions import init_permissions
            await init_permissions()
            logger.info("✅ Security permissions initialized")
        except Exception as e:
            logger.warning(f"⚠️  Security initialization warning: {str(e)}")

        try:
            # Assuming MonitoringService is the correct name based on your prompt text
            from .services.monitoring_service import MonitoringService
            monitoring_service = MonitoringService()
            app.state.monitoring_service = monitoring_service
            logger.info("✅ Monitoring service initialized")
        except ImportError:
            logger.warning("⚠️ MonitoringService not found, skipping initialization.")
            app.state.monitoring_service = None
        except Exception as e:
            logger.warning(f"⚠️  Monitoring service initialization failed: {str(e)}")

        # --- FINAL STARTUP LOGS ---
        logger.info(f"✅ Total API endpoints registered: {len(app.routes)}")
        try:
            # Assuming _get_system_metrics exists in your monitoring API
            from .api.monitoring import _get_system_metrics
            initial_metrics = await _get_system_metrics()
            logger.info(f"✅ Initial system metrics: CPU {initial_metrics.get('cpu_usage_percent', 0):.1f}%, Memory {initial_metrics.get('memory_usage_percent', 0):.1f}%")
        except Exception:
            logger.warning("⚠️  Could not perform initial system metrics check.")

        logger.info("🎉 UGENE Web Platform startup completed successfully")
        yield

    except Exception as e:
        logger.error(f"❌ CRITICAL STARTUP ERROR: {str(e)}", exc_info=True)
        yield # Still yield to allow the app to run for debugging, even if startup fails

    finally:
        # --- SHUTDOWN LOGIC ---
        logger.info("🔄 Shutting down services...")
        if db_manager:
            try:
                await db_manager.close_connection()
                logger.info("✅ Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
        if cache_manager and hasattr(cache_manager, 'close'):
             try:
                await cache_manager.close()
                logger.info("✅ Cache connection closed")
             except Exception as e:
                logger.error(f"Error closing cache connection: {str(e)}")
        logger.info("✅ Shutdown completed.")


# --- API DOCUMENTATION METADATA ---
tags_metadata = [
    {"name": "System", "description": "System health, status, and information."},
    {"name": "Sequences", "description": "Endpoints for managing biological sequences."},
    {"name": "Workflows", "description": "Design, execution, and management of bioinformatics workflows."},
    {"name": "Analysis", "description": "Endpoints for running various bioinformatics analyses."},
    {"name": "Files", "description": "File upload and management."},
    {"name": "Data Writers", "description": "Export data to various biological formats."},
    {"name": "Data Converters", "description": "Convert between different data formats."},
    {"name": "Data Flow", "description": "Manage workflow data transformations."},
    {"name": "DNA Assembly", "description": "Genome assembly algorithms and quality assessment."},
    {"name": "NGS Mapping", "description": "Next-generation sequencing read mapping."},
    {"name": "NGS Variant Analysis", "description": "Variant calling and annotation."},
    {"name": "System Monitoring", "description": "System performance and health monitoring."},
    {"name": "System Administration", "description": "Administrative operations (requires admin access)."},
    {"name": "WebSocket", "description": "Real-time communication and progress tracking."},
]

# --- FASTAPI APP INSTANTIATION ---
app = FastAPI(
    title="UGENE Web Platform - Comprehensive Bioinformatics API",
    description="A modern, web-based bioinformatics platform for sequence analysis, workflow execution, and data management.",
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "UGENE Web Platform Support",
        "url": "https://ugene.net",
        "email": "support@ugene.net"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# --- MIDDLEWARE REGISTRATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and add process time header."""
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)
    if not request.url.path.endswith(('/health', '/metrics')):
        logger.info(f'{request.method} {request.url.path} - Status {response.status_code} - Took {process_time:.4f}s')
    return response

# Load Middleware with graceful failure
try:
    from .middleware.rate_limiting import RateLimitingMiddleware
    app.add_middleware(RateLimitingMiddleware)
    logger.info("✅ Rate limiting middleware enabled")
except Exception as e:
    logger.warning(f"⚠️ Failed to load rate limiting middleware: {str(e)}")

# --- API ROUTER INCLUSION ---
# Load routers with graceful failure to ensure app starts even if a module is broken.
routers_to_load = [
    ("api.sequences", "sequences_router", "/api/v1", ["Sequences"]),
    ("api.workflow_elements", "router", "/api/v1", ["Workflows"]),
    ("api.workflows", "router", "/api/v1", ["Workflow Management"]),
    ("api.enhanced_endpoints", "router", "", ["Enhanced API"]),
    ("api.data_writers", "router", "/api/v1", ["Data Writers"]),
    ("api.data_converters", "router", "/api/v1", ["Data Converters"]),
    ("api.data_flow", "router", "/api/v1", ["Data Flow"]),
    ("api.dna_assembly", "router", "/api/v1", ["DNA Assembly"]),
    ("api.ngs_mapping", "router", "/api/v1", ["NGS Mapping"]),
    ("api.monitoring", "router", "/api/v1", ["System Monitoring"]),
    ("api.system_admin", "router", "/api/v1", ["System Administration"]),
    ("api.ngs_variant", "router", "/api/v1", ["NGS Variant Analysis"]),
    ("api.notification_endpoints", "router", "/api/v1", ["Notifications"]),
    ("api.websocket_endpoints", "router", "/ws", ["WebSocket"]),
]

for module_name, router_name, prefix, tags in routers_to_load:
    try:
        module = __import__(f"app.{module_name}", fromlist=[router_name])
        router = getattr(module, router_name)
        app.include_router(router, prefix=prefix, tags=tags)
        logger.info(f"✅ {tags[0]} API router loaded successfully.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load {tags[0]} router from {module_name}: {str(e)}")


# --- EXCEPTION HANDLERS ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler with security event logging."""
    logger.error(f"HTTP {exc.status_code} error on {request.url.path}: {exc.detail}")
    if exc.status_code in [401, 403, 429]:
        await _log_security_event(request, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "path": str(request.url),
            "timestamp": datetime.utcnow().isoformat()
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Enhanced general exception handler for unhandled errors."""
    error_id = f"err_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    logger.error(f"Unhandled exception (ID: {error_id}) on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected internal server error occurred.",
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        },
    )

# --- CORE & MOCK ENDPOINTS ---
@app.get("/", tags=["System"])
async def root():
    """Root endpoint providing basic application status."""
    return {
        "message": "Welcome to the UGENE Web Platform API",
        "version": app.version,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", tags=["System"])
async def health_check(request: Request):
    """Provides a comprehensive health check of the application and its services."""
    health_status = {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "services": {}}
    
    # Check Database
    db_manager = getattr(request.app.state, 'db_manager', None)
    if db_manager:
        try:
            await db_manager.database.command("ping")
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["database"] = "unavailable"
        health_status["status"] = "degraded"

    # Check Cache
    cache_manager = getattr(request.app.state, 'cache_manager', None)
    if cache_manager:
        try:
            await cache_manager.ping()
            health_status["services"]["cache"] = "healthy"
        except Exception as e:
            health_status["services"]["cache"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["cache"] = "unavailable"

    # Check Docker
    external_tools = getattr(request.app.state, 'external_tools', None)
    if external_tools:
        if external_tools._is_docker_available():
            health_status["services"]["docker"] = "healthy"
        else:
            health_status["services"]["docker"] = "unavailable"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["docker"] = "unavailable"

    return health_status


# This can be expanded into a full-fledged mock data generator for development
def get_mock_sequences():
    """Provides mock sequence data when the database is unavailable."""
    return [
        {"id": "mock_dna_1", "name": "Mock DNA Sequence", "sequence": "ATGCGTACGT", "sequence_type": "DNA"},
        {"id": "mock_prot_1", "name": "Mock Protein Sequence", "sequence": "MVRQSP", "sequence_type": "PROTEIN"}
    ]

@app.get("/api/v1/sequences", tags=["Sequences"])
async def list_sequences(request: Request):
    """Lists available sequences, using the database if available, otherwise returns mock data."""
    db = request.app.state.db_manager
    if db:
        sequences_collection = await db.get_collection("sequences")
        # Convert ObjectId to string for JSON serialization
        sequences = []
        async for seq in sequences_collection.find({}).limit(50):
            seq['_id'] = str(seq['_id'])
            sequences.append(seq)
        return sequences
    return get_mock_sequences()


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"Starting server at http://{host}:{port} with reload={'enabled' if reload else 'disabled'}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload, log_level=log_level)
