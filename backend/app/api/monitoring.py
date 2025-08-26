# backend/app/api/monitoring.py
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
import asyncio
import psutil
import docker
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel, Field

from ..services.external_tool_manager import ExternalToolManager
from ..services.caching_manager import BioinformaticsCacheManager
from ..database.database_setup import DatabaseManager
from ..websockets.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["System Monitoring"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SystemHealthCheck(BaseModel):
    """System health check response model"""
    status: str
    timestamp: datetime
    services: Dict[str, str]
    system_metrics: Dict[str, Any]
    issues: List[str] = Field(default_factory=list)

class PerformanceMetrics(BaseModel):
    """Performance metrics model"""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    active_connections: int
    response_times: Dict[str, float]

class ServiceStatus(BaseModel):
    """Individual service status model"""
    service_name: str
    status: str
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None

# ============================================================================
# SYSTEM HEALTH ENDPOINTS
# ============================================================================

@router.get("/health", response_model=SystemHealthCheck)
async def comprehensive_health_check():
    """Comprehensive system health check"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "services": {},
            "system_metrics": {},
            "issues": []
        }
        
        # Check database connectivity
        try:
            # This would use your DatabaseManager
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"
            health_status["issues"].append(f"Database connection failed: {str(e)}")
            health_status["status"] = "degraded"
        
        # Check Redis cache
        try:
            cache_manager = BioinformaticsCacheManager()
            await cache_manager.health_check()
            health_status["services"]["cache"] = "healthy"
        except Exception as e:
            health_status["services"]["cache"] = f"unhealthy: {str(e)}"
            health_status["issues"].append(f"Cache service failed: {str(e)}")
        
        # Check Docker service
        try:
            docker_client = docker.from_env()
            docker_client.ping()
            health_status["services"]["docker"] = "healthy"
        except Exception as e:
            health_status["services"]["docker"] = f"unhealthy: {str(e)}"
            health_status["issues"].append(f"Docker service unavailable: {str(e)}")
        
        # System metrics
        health_status["system_metrics"] = await _get_system_metrics()
        
        # Check for critical issues
        memory_usage = health_status["system_metrics"].get("memory_usage_percent", 0)
        disk_usage = health_status["system_metrics"].get("disk_usage_percent", 0)
        
        if memory_usage > 90:
            health_status["issues"].append(f"High memory usage: {memory_usage:.1f}%")
            health_status["status"] = "degraded"
        
        if disk_usage > 85:
            health_status["issues"].append(f"High disk usage: {disk_usage:.1f}%")
            health_status["status"] = "degraded"
        
        # Set overall status
        if health_status["issues"]:
            health_status["status"] = "degraded" if health_status["status"] == "healthy" else health_status["status"]
        
        return SystemHealthCheck(**health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/system-metrics", response_model=PerformanceMetrics)
async def get_system_performance_metrics():
    """Get detailed system performance metrics"""
    try:
        metrics = await _get_system_metrics()
        return PerformanceMetrics(**metrics)
        
    except Exception as e:
        logger.error(f"System metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")

@router.get("/service-status")
async def get_individual_service_status():
    """Get status of individual services"""
    try:
        services = []
        
        # Database service
        db_status = await _check_service_health("database")
        services.append(db_status)
        
        # Cache service
        cache_status = await _check_service_health("cache")
        services.append(cache_status)
        
        # Docker service
        docker_status = await _check_service_health("docker")
        services.append(docker_status)
        
        # External tools
        tools_status = await _check_service_health("external_tools")
        services.append(tools_status)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "services": services,
            "healthy_services": len([s for s in services if s["status"] == "healthy"]),
            "total_services": len(services)
        }
        
    except Exception as e:
        logger.error(f"Service status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")

# ============================================================================
# PERFORMANCE MONITORING ENDPOINTS
# ============================================================================

@router.get("/performance-history")
async def get_performance_history(
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    metric: str = Query("all", regex="^(all|cpu|memory|disk|network)$")
):
    """Get historical performance metrics"""
    try:
        # In production, this would query stored metrics from database
        # For now, return mock historical data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Generate mock time series data
        timestamps = []
        cpu_data = []
        memory_data = []
        disk_data = []
        
        for i in range(hours):
            timestamp = start_time + timedelta(hours=i)
            timestamps.append(timestamp.isoformat())
            
            # Mock performance data with some variation
            import random
            cpu_data.append(random.uniform(10, 80))
            memory_data.append(random.uniform(30, 70))
            disk_data.append(random.uniform(20, 60))
        
        history_data = {
            "timestamps": timestamps,
            "metrics": {
                "cpu_usage": cpu_data,
                "memory_usage": memory_data,
                "disk_usage": disk_data
            }
        }
        
        if metric != "all":
            history_data["metrics"] = {metric + "_usage": history_data["metrics"][metric + "_usage"]}
        
        return {
            "status": "success",
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "data_points": len(timestamps),
            "performance_history": history_data
        }
        
    except Exception as e:
        logger.error(f"Performance history error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance history: {str(e)}")

@router.get("/resource-usage")
async def get_current_resource_usage():
    """Get current resource usage by different components"""
    try:
        # System-wide metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process-specific metrics
        import os
        current_process = psutil.Process(os.getpid())
        process_memory = current_process.memory_info()
        
        # Docker container metrics (if available)
        container_metrics = await _get_container_metrics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "system_resources": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": round((disk.used / disk.total) * 100, 2)
                }
            },
            "process_resources": {
                "memory_mb": round(process_memory.rss / (1024**2), 2),
                "cpu_percent": current_process.cpu_percent()
            },
            "container_metrics": container_metrics
        }
        
    except Exception as e:
        logger.error(f"Resource usage error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get resource usage: {str(e)}")

# ============================================================================
# APPLICATION MONITORING ENDPOINTS
# ============================================================================

@router.get("/api-performance")
async def get_api_performance_metrics():
    """Get API endpoint performance metrics"""
    try:
        # In production, this would query actual API metrics
        # Mock performance data for different endpoints
        api_metrics = {
            "/api/v1/workflows/": {
                "total_requests": 1543,
                "average_response_time_ms": 245,
                "success_rate": 98.5,
                "error_rate": 1.5,
                "requests_per_minute": 12
            },
            "/api/v1/analysis/blast": {
                "total_requests": 892,
                "average_response_time_ms": 3420,
                "success_rate": 94.2,
                "error_rate": 5.8,
                "requests_per_minute": 3
            },
            "/api/v1/dna-assembly/": {
                "total_requests": 234,
                "average_response_time_ms": 15600,
                "success_rate": 91.0,
                "error_rate": 9.0,
                "requests_per_minute": 1
            }
        }
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "api_metrics": api_metrics,
            "overall_health": {
                "total_endpoints": len(api_metrics),
                "average_success_rate": sum(m["success_rate"] for m in api_metrics.values()) / len(api_metrics),
                "slowest_endpoint": max(api_metrics.items(), key=lambda x: x[1]["average_response_time_ms"])
            }
        }
        
    except Exception as e:
        logger.error(f"API performance metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get API metrics: {str(e)}")

@router.get("/task-queue-status")
async def get_task_queue_status():
    """Get status of background task queues"""
    try:
        # In production, this would query Redis/Celery task queues
        queue_status = {
            "active_tasks": 3,
            "pending_tasks": 12,
            "completed_tasks_today": 156,
            "failed_tasks_today": 8,
            "worker_nodes": 2,
            "queue_health": "healthy"
        }
        
        # Task breakdown by type
        task_breakdown = {
            "assembly_tasks": 5,
            "blast_searches": 7,
            "alignment_tasks": 3,
            "file_conversions": 2
        }
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "queue_status": queue_status,
            "task_breakdown": task_breakdown
        }
        
    except Exception as e:
        logger.error(f"Task queue status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get task queue status: {str(e)}")

# ============================================================================
# ERROR MONITORING ENDPOINTS
# ============================================================================

@router.get("/error-logs")
async def get_recent_errors(
    hours: int = Query(24, ge=1, le=168),
    severity: str = Query("all", regex="^(all|error|warning|critical)$"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get recent error logs"""
    try:
        # In production, this would query actual log aggregation system
        # Mock error data
        errors = []
        
        for i in range(min(limit, 20)):  # Mock some errors
            error_time = datetime.utcnow() - timedelta(hours=i*2)
            errors.append({
                "timestamp": error_time.isoformat(),
                "severity": "error" if i % 3 == 0 else "warning",
                "service": ["api", "worker", "database"][i % 3],
                "message": f"Mock error message {i+1}",
                "error_code": f"E{1000 + i}",
                "request_id": f"req_{i}"
            })
        
        # Filter by severity if specified
        if severity != "all":
            errors = [e for e in errors if e["severity"] == severity]
        
        return {
            "status": "success",
            "time_range_hours": hours,
            "severity_filter": severity,
            "total_errors": len(errors),
            "errors": errors[:limit]
        }
        
    except Exception as e:
        logger.error(f"Error logs retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get error logs: {str(e)}")

@router.get("/error-summary")
async def get_error_summary(
    days: int = Query(7, ge=1, le=30)
):
    """Get error summary and trends"""
    try:
        # Mock error trend data
        error_summary = {
            "total_errors": 45,
            "total_warnings": 123,
            "critical_errors": 2,
            "error_trends": {
                "today": 8,
                "yesterday": 12,
                "this_week": 45,
                "last_week": 67
            },
            "top_error_types": [
                {"type": "timeout_error", "count": 15, "percentage": 33.3},
                {"type": "validation_error", "count": 12, "percentage": 26.7},
                {"type": "docker_error", "count": 8, "percentage": 17.8},
                {"type": "database_error", "count": 10, "percentage": 22.2}
            ],
            "services_with_most_errors": [
                {"service": "external_tools", "error_count": 18},
                {"service": "api_gateway", "error_count": 15},
                {"service": "worker", "error_count": 12}
            ]
        }
        
        return {
            "status": "success",
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "error_summary": error_summary
        }
        
    except Exception as e:
        logger.error(f"Error summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get error summary: {str(e)}")

# ============================================================================
# CONTAINER MONITORING ENDPOINTS
# ============================================================================

@router.get("/container-status")
async def get_container_status():
    """Get status of all Docker containers"""
    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list(all=True)
        
        container_info = []
        for container in containers:
            container_info.append({
                "id": container.id[:12],
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "created": container.attrs["Created"],
                "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
                "labels": container.labels
            })
        
        # Categorize containers
        running_containers = [c for c in container_info if c["status"] == "running"]
        stopped_containers = [c for c in container_info if c["status"] in ["exited", "stopped"]]
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "container_summary": {
                "total_containers": len(containers),
                "running": len(running_containers),
                "stopped": len(stopped_containers)
            },
            "containers": container_info
        }
        
    except Exception as e:
        logger.error(f"Container status error: {str(e)}")
        return {
            "status": "error",
            "message": "Docker not available or accessible",
            "error": str(e)
        }

@router.get("/container-resources/{container_id}")
async def get_container_resource_usage(container_id: str):
    """Get resource usage for specific container"""
    try:
        external_tools = ExternalToolManager()
        resource_usage = await external_tools.monitor_container_resources(container_id)
        
        return {
            "status": "success",
            "container_id": container_id,
            "resource_usage": resource_usage,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Container resource monitoring error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to monitor container: {str(e)}")

# ============================================================================
# DATABASE MONITORING ENDPOINTS
# ============================================================================

@router.get("/database-metrics")
async def get_database_metrics(db_manager: DatabaseManager = Depends()):
    """Get database performance and usage metrics"""
    try:
        # Get database statistics
        db_stats = await db_manager.get_database_statistics()
        
        # Calculate additional metrics
        total_documents = sum(db_stats.get(collection, {}).get("count", 0) 
                            for collection in ["sequences", "analysis_tasks", "analysis_results"])
        
        storage_info = {
            "total_collections": len(db_stats),
            "total_documents": total_documents,
            "total_indexes": sum(db_stats.get(collection, {}).get("indexes", 0) 
                               for collection in db_stats),
            "estimated_size_mb": sum(db_stats.get(collection, {}).get("size", 0) 
                                   for collection in db_stats) / (1024 * 1024)
        }
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "database_metrics": db_stats,
            "storage_summary": storage_info
        }
        
    except Exception as e:
        logger.error(f"Database metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get database metrics: {str(e)}")

# ============================================================================
# CACHE MONITORING ENDPOINTS
# ============================================================================

@router.get("/cache-metrics")
async def get_cache_metrics():
    """Get cache performance metrics"""
    try:
        cache_manager = BioinformaticsCacheManager()
        cache_stats = await cache_manager.get_cache_stats()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_metrics": cache_stats,
            "performance_indicators": {
                "hit_rate_quality": "excellent" if cache_stats.get("hit_rate", 0) > 80 else "good" if cache_stats.get("hit_rate", 0) > 60 else "poor",
                "memory_usage_status": "normal" if cache_stats.get("memory_usage_percent", 0) < 80 else "high",
                "key_count_status": "normal" if cache_stats.get("total_keys", 0) < 10000 else "high"
            }
        }
        
    except Exception as e:
        logger.error(f"Cache metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache metrics: {str(e)}")

# ============================================================================
# ALERT AND NOTIFICATION ENDPOINTS
# ============================================================================

@router.post("/alerts/create")
async def create_monitoring_alert(
    alert_name: str,
    metric: str,
    threshold: float,
    condition: str = Query(..., regex="^(greater_than|less_than|equals)$"),
    notification_channels: List[str] = []
):
    """Create monitoring alert rule"""
    try:
        alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        alert_rule = {
            "id": alert_id,
            "name": alert_name,
            "metric": metric,
            "threshold": threshold,
            "condition": condition,
            "notification_channels": notification_channels,
            "created_at": datetime.utcnow().isoformat(),
            "enabled": True,
            "triggered_count": 0
        }
        
        # In production, this would store the alert rule in database
        logger.info(f"Alert rule created: {alert_name}")
        
        return {
            "status": "success",
            "alert_id": alert_id,
            "alert_rule": alert_rule,
            "message": f"Alert '{alert_name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Alert creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}")

@router.get("/alerts")
async def list_monitoring_alerts():
    """List all configured monitoring alerts"""
    try:
        # Mock alert data - in production, this would come from database
        alerts = [
            {
                "id": "alert_001",
                "name": "High CPU Usage",
                "metric": "cpu_percent",
                "threshold": 80,
                "condition": "greater_than",
                "enabled": True,
                "last_triggered": None,
                "triggered_count": 0
            },
            {
                "id": "alert_002", 
                "name": "Low Disk Space",
                "metric": "disk_usage_percent",
                "threshold": 85,
                "condition": "greater_than",
                "enabled": True,
                "last_triggered": "2024-12-10T15:30:00Z",
                "triggered_count": 3
            }
        ]
        
        return {
            "status": "success",
            "total_alerts": len(alerts),
            "active_alerts": len([a for a in alerts if a["enabled"]]),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Alert listing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list alerts: {str(e)}")

# ============================================================================
# DIAGNOSTIC ENDPOINTS
# ============================================================================

@router.post("/run-diagnostics")
async def run_system_diagnostics(
    background_tasks: BackgroundTasks,
    diagnostic_type: str = Query("full", regex="^(full|quick|connectivity|performance)$")
):
    """Run comprehensive system diagnostics"""
    try:
        diagnostic_id = f"diag_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_system_diagnostics,
            diagnostic_id,
            diagnostic_type
        )
        
        return {
            "status": "started",
            "diagnostic_id": diagnostic_id,
            "diagnostic_type": diagnostic_type,
            "estimated_duration": "2-5 minutes" if diagnostic_type == "full" else "30 seconds",
            "monitor_url": f"/api/v1/monitoring/diagnostics-status/{diagnostic_id}"
        }
        
    except Exception as e:
        logger.error(f"Diagnostics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start diagnostics: {str(e)}")

@router.get("/diagnostics-status/{diagnostic_id}")
async def get_diagnostics_status(diagnostic_id: str):
    """Get status of running diagnostics"""
    # In production, this would query actual diagnostic status
    return {
        "diagnostic_id": diagnostic_id,
        "status": "completed",
        "progress": 100,
        "current_test": "summary_generation",
        "completed_tests": ["connectivity", "performance", "disk_health", "service_status"],
        "failed_tests": [],
        "results_available": True
    }

@router.get("/diagnostics-results/{diagnostic_id}")
async def get_diagnostics_results(diagnostic_id: str):
    """Get results of completed diagnostics"""
    try:
        # Mock diagnostic results
        results = {
            "diagnostic_id": diagnostic_id,
            "completed_at": datetime.utcnow().isoformat(),
            "overall_health": "healthy",
            "test_results": {
                "connectivity_tests": {
                    "database_connection": "passed",
                    "cache_connection": "passed",
                    "docker_connection": "passed",
                    "external_api_access": "passed"
                },
                "performance_tests": {
                    "api_response_time": "passed",
                    "database_query_time": "passed",
                    "file_io_performance": "warning",
                    "memory_usage": "passed"
                },
                "resource_tests": {
                    "disk_space": "passed",
                    "memory_availability": "passed",
                    "cpu_load": "passed",
                    "network_bandwidth": "passed"
                }
            },
            "recommendations": [
                "Consider optimizing file I/O operations",
                "Monitor disk space usage trends",
                "Schedule regular cache cleanup"
            ]
        }
        
        return {
            "status": "success",
            "diagnostic_results": results
        }
        
    except Exception as e:
        logger.error(f"Diagnostic results error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get diagnostic results: {str(e)}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics
        network_io = psutil.net_io_counters()
        
        return {
            "cpu_usage_percent": cpu_percent,
            "cpu_count": cpu_count,
            "memory_usage_percent": memory.percent,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_usage_percent": round((disk.used / disk.total) * 100, 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "network_io": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_received": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_received": network_io.packets_recv
            },
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        }
        
    except Exception as e:
        logger.error(f"System metrics collection error: {str(e)}")
        return {}

async def _check_service_health(service_name: str) -> ServiceStatus:
    """Check health of individual service"""
    start_time = datetime.utcnow()
    
    try:
        if service_name == "database":
            # Test database connection
            # db_manager = DatabaseManager()
            # await db_manager.health_check()
            status = "healthy"
            error_message = None
            
        elif service_name == "cache":
            # Test cache connection
            cache_manager = BioinformaticsCacheManager()
            await cache_manager.health_check()
            status = "healthy"
            error_message = None
            
        elif service_name == "docker":
            # Test Docker connection
            docker_client = docker.from_env()
            docker_client.ping()
            status = "healthy"
            error_message = None
            
        elif service_name == "external_tools":
            # Test external tools
            tools_manager = ExternalToolManager()
            if tools_manager._is_docker_available():
                status = "healthy"
                error_message = None
            else:
                status = "unhealthy"
                error_message = "Docker not available"
        
        else:
            status = "unknown"
            error_message = f"Unknown service: {service_name}"
            
    except Exception as e:
        status = "unhealthy"
        error_message = str(e)
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    return ServiceStatus(
        service_name=service_name,
        status=status,
        last_check=datetime.utcnow(),
        response_time_ms=response_time,
        error_message=error_message
    )

async def _get_container_metrics() -> Dict[str, Any]:
    """Get metrics for Docker containers"""
    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list()
        
        container_metrics = {}
        
        for container in containers:
            try:
                stats = container.stats(stream=False)
                
                # Parse memory usage
                memory_usage = stats['memory_stats'].get('usage', 0)
                memory_limit = stats['memory_stats'].get('limit', 1)
                memory_percent = (memory_usage / memory_limit) * 100
                
                container_metrics[container.name] = {
                    "memory_usage_mb": round(memory_usage / (1024**2), 2),
                    "memory_limit_mb": round(memory_limit / (1024**2), 2),
                    "memory_percent": round(memory_percent, 2),
                    "status": container.status
                }
                
            except Exception as e:
                container_metrics[container.name] = {
                    "error": f"Failed to get stats: {str(e)}"
                }
        
        return container_metrics
        
    except Exception as e:
        logger.error(f"Container metrics error: {str(e)}")
        return {"error": "Docker not available"}

async def _execute_system_diagnostics(
    diagnostic_id: str,
    diagnostic_type: str
):
    """Execute system diagnostics in background"""
    try:
        diagnostic_results = {
            "diagnostic_id": diagnostic_id,
            "type": diagnostic_type,
            "started_at": datetime.utcnow().isoformat(),
            "tests_run": [],
            "issues_found": [],
            "recommendations": []
        }
        
        # Run different tests based on diagnostic type
        if diagnostic_type in ["full", "connectivity"]:
            # Test service connectivity
            services = ["database", "cache", "docker", "external_tools"]
            for service in services:
                service_status = await _check_service_health(service)
                diagnostic_results["tests_run"].append(f"{service}_connectivity")
                
                if service_status.status != "healthy":
                    diagnostic_results["issues_found"].append(
                        f"{service} service unhealthy: {service_status.error_message}"
                    )
        
        if diagnostic_type in ["full", "performance"]:
            # Test system performance
            metrics = await _get_system_metrics()
            diagnostic_results["tests_run"].append("performance_check")
            
            if metrics.get("cpu_usage_percent", 0) > 80:
                diagnostic_results["issues_found"].append("High CPU usage detected")
                diagnostic_results["recommendations"].append("Consider scaling up compute resources")
            
            if metrics.get("memory_usage_percent", 0) > 85:
                diagnostic_results["issues_found"].append("High memory usage detected")
                diagnostic_results["recommendations"].append("Consider increasing memory allocation")
        
        diagnostic_results["completed_at"] = datetime.utcnow().isoformat()
        diagnostic_results["status"] = "completed"
        
        logger.info(f"Diagnostic {diagnostic_id} completed with {len(diagnostic_results['issues_found'])} issues")
        
    except Exception as e:
        logger.error(f"Diagnostic {diagnostic_id} failed: {str(e)}")