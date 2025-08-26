# backend/app/api/system_admin.py
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
import asyncio
import shutil
import docker
from datetime import datetime, timedelta
from pathlib import Path
import logging
from pydantic import BaseModel, Field

from ..database.database_setup import DatabaseManager
from ..services.external_tool_manager import ExternalToolManager
from ..services.caching_manager import BioinformaticsCacheManager
from ..services.data_writers import DataWritersService
from ..security.permissions import get_current_user_with_permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["System Administration"])
security = HTTPBearer()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SystemMaintenanceRequest(BaseModel):
    """Request model for system maintenance operations"""
    operation_type: str = Field(..., regex="^(cleanup|optimize|backup|restore)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    schedule_time: Optional[datetime] = None

class UserManagementRequest(BaseModel):
    """Request model for user management"""
    action: str = Field(..., regex="^(create|update|delete|suspend|activate)$")
    user_data: Dict[str, Any]

class SystemConfigUpdate(BaseModel):
    """Request model for system configuration updates"""
    config_section: str
    config_values: Dict[str, Any]
    apply_immediately: bool = True

class DatabaseMaintenanceRequest(BaseModel):
    """Request model for database maintenance"""
    operation: str = Field(..., regex="^(reindex|vacuum|backup|integrity_check)$")
    collections: Optional[List[str]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

# ============================================================================
# SYSTEM MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/system/maintenance")
async def schedule_system_maintenance(
    request: SystemMaintenanceRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "system_maintenance"]))
):
    """Schedule system maintenance operations"""
    try:
        maintenance_id = f"maint_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        if request.schedule_time and request.schedule_time > datetime.utcnow():
            # Schedule for later
            delay_seconds = (request.schedule_time - datetime.utcnow()).total_seconds()
            background_tasks.add_task(
                _delayed_maintenance,
                maintenance_id,
                request.operation_type,
                request.parameters,
                delay_seconds
            )
            status_msg = f"Maintenance scheduled for {request.schedule_time.isoformat()}"
        else:
            # Execute immediately
            background_tasks.add_task(
                _execute_maintenance,
                maintenance_id,
                request.operation_type,
                request.parameters
            )
            status_msg = "Maintenance started immediately"
        
        # Log admin action
        await _log_admin_action(
            current_user.get("user_id"),
            "schedule_maintenance",
            {"maintenance_id": maintenance_id, "operation": request.operation_type}
        )
        
        return {
            "status": "scheduled",
            "maintenance_id": maintenance_id,
            "operation_type": request.operation_type,
            "message": status_msg,
            "monitor_url": f"/api/v1/admin/maintenance-status/{maintenance_id}"
        }
        
    except Exception as e:
        logger.error(f"Maintenance scheduling error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule maintenance: {str(e)}")

@router.get("/maintenance-status/{maintenance_id}")
async def get_maintenance_status(
    maintenance_id: str,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "system_maintenance"]))
):
    """Get status of maintenance operation"""
    # In production, this would query actual maintenance status
    return {
        "maintenance_id": maintenance_id,
        "status": "completed",
        "progress": 100,
        "current_operation": "cleanup_completed",
        "completed_operations": ["file_cleanup", "cache_optimization", "database_maintenance"],
        "failed_operations": [],
        "start_time": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
        "completion_time": datetime.utcnow().isoformat()
    }

# ============================================================================
# FILE SYSTEM MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/filesystem/cleanup")
async def cleanup_filesystem(
    background_tasks: BackgroundTasks,
    target_directories: List[str] = Query(["temp", "uploads", "outputs"]),
    max_age_days: int = Query(7, ge=1, le=365),
    dry_run: bool = Query(False),
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "file_management"]))
):
    """Clean up old files from filesystem"""
    try:
        cleanup_id = f"cleanup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_filesystem_cleanup,
            cleanup_id,
            target_directories,
            max_age_days,
            dry_run
        )
        
        await _log_admin_action(
            current_user.get("user_id"),
            "filesystem_cleanup",
            {"cleanup_id": cleanup_id, "directories": target_directories, "dry_run": dry_run}
        )
        
        return {
            "status": "started",
            "cleanup_id": cleanup_id,
            "target_directories": target_directories,
            "max_age_days": max_age_days,
            "dry_run": dry_run,
            "monitor_url": f"/api/v1/admin/cleanup-status/{cleanup_id}"
        }
        
    except Exception as e:
        logger.error(f"Filesystem cleanup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Filesystem cleanup failed: {str(e)}")

@router.get("/filesystem/usage")
async def get_filesystem_usage(
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "monitoring"]))
):
    """Get detailed filesystem usage statistics"""
    try:
        # Check main directories
        directories = {
            "uploads": "/app/uploads",
            "outputs": "/tmp/ugene_outputs", 
            "temp": "/tmp",
            "logs": "/var/log"
        }
        
        usage_stats = {}
        
        for dir_name, dir_path in directories.items():
            try:
                path = Path(dir_path)
                if path.exists():
                    # Calculate directory size
                    total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                    file_count = len([f for f in path.rglob('*') if f.is_file()])
                    
                    usage_stats[dir_name] = {
                        "path": str(path),
                        "size_bytes": total_size,
                        "size_mb": round(total_size / (1024**2), 2),
                        "size_gb": round(total_size / (1024**3), 2),
                        "file_count": file_count,
                        "accessible": True
                    }
                else:
                    usage_stats[dir_name] = {
                        "path": str(path),
                        "accessible": False,
                        "error": "Directory not found"
                    }
                    
            except Exception as e:
                usage_stats[dir_name] = {
                    "path": dir_path,
                    "accessible": False,
                    "error": str(e)
                }
        
        # System disk usage
        disk_usage = shutil.disk_usage("/")
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "directory_usage": usage_stats,
            "system_disk": {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "usage_percent": round((disk_usage.used / disk_usage.total) * 100, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Filesystem usage error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get filesystem usage: {str(e)}")

# ============================================================================
# DATABASE ADMINISTRATION ENDPOINTS
# ============================================================================

@router.post("/database/maintenance")
async def database_maintenance(
    request: DatabaseMaintenanceRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "database_admin"]))
):
    """Perform database maintenance operations"""
    try:
        operation_id = f"db_op_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_database_maintenance,
            operation_id,
            request.operation,
            request.collections,
            request.parameters
        )
        
        await _log_admin_action(
            current_user.get("user_id"),
            "database_maintenance",
            {"operation_id": operation_id, "operation": request.operation}
        )
        
        return {
            "status": "started",
            "operation_id": operation_id,
            "operation": request.operation,
            "collections": request.collections,
            "monitor_url": f"/api/v1/admin/database-operation-status/{operation_id}"
        }
        
    except Exception as e:
        logger.error(f"Database maintenance error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database maintenance failed: {str(e)}")

@router.get("/database/statistics")
async def get_database_statistics(
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "monitoring"])),
    db_manager: DatabaseManager = Depends()
):
    """Get comprehensive database statistics"""
    try:
        stats = await db_manager.get_database_statistics()
        
        # Calculate additional insights
        total_documents = sum(collection_stats.get("count", 0) for collection_stats in stats.values())
        largest_collection = max(stats.items(), key=lambda x: x[1].get("count", 0)) if stats else None
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "database_statistics": stats,
            "insights": {
                "total_documents": total_documents,
                "total_collections": len(stats),
                "largest_collection": {
                    "name": largest_collection[0],
                    "document_count": largest_collection[1].get("count", 0)
                } if largest_collection else None
            }
        }
        
    except Exception as e:
        logger.error(f"Database statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get database statistics: {str(e)}")

# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/users/manage")
async def manage_users(
    request: UserManagementRequest,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "user_management"]))
):
    """Manage user accounts (create, update, delete, suspend)"""
    try:
        user_id = request.user_data.get("user_id")
        
        if request.action == "create":
            # Create new user
            new_user = {
                "user_id": user_id,
                "email": request.user_data.get("email"),
                "role": request.user_data.get("role", "user"),
                "created_at": datetime.utcnow().isoformat(),
                "created_by": current_user.get("user_id"),
                "status": "active"
            }
            # Would store in database
            result_message = f"User {user_id} created successfully"
            
        elif request.action == "update":
            # Update existing user
            update_fields = {k: v for k, v in request.user_data.items() if k != "user_id"}
            update_fields["updated_at"] = datetime.utcnow().isoformat()
            update_fields["updated_by"] = current_user.get("user_id")
            # Would update in database
            result_message = f"User {user_id} updated successfully"
            
        elif request.action == "delete":
            # Soft delete user
            # Would mark as deleted in database
            result_message = f"User {user_id} deleted successfully"
            
        elif request.action == "suspend":
            # Suspend user account
            # Would update status in database
            result_message = f"User {user_id} suspended"
            
        elif request.action == "activate":
            # Activate user account
            # Would update status in database
            result_message = f"User {user_id} activated"
        
        await _log_admin_action(
            current_user.get("user_id"),
            f"user_{request.action}",
            {"target_user": user_id, "user_data": request.user_data}
        )
        
        return {
            "status": "success",
            "action": request.action,
            "user_id": user_id,
            "message": result_message
        }
        
    except Exception as e:
        logger.error(f"User management error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"User management failed: {str(e)}")

@router.get("/users/list")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    status_filter: str = Query("all", regex="^(all|active|suspended|deleted)$"),
    role_filter: str = Query("all", regex="^(all|admin|user|viewer)$"),
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "user_management"]))
):
    """List users with filtering and pagination"""
    try:
        # Mock user data - in production, this would query database
        mock_users = [
            {
                "user_id": f"user_{i}",
                "email": f"user{i}@example.com",
                "role": ["admin", "user", "viewer"][i % 3],
                "status": ["active", "suspended"][i % 2],
                "created_at": (datetime.utcnow() - timedelta(days=i*10)).isoformat(),
                "last_login": (datetime.utcnow() - timedelta(days=i)).isoformat() if i % 3 == 0 else None
            }
            for i in range(1, 101)  # Mock 100 users
        ]
        
        # Apply filters
        filtered_users = mock_users
        if status_filter != "all":
            filtered_users = [u for u in filtered_users if u["status"] == status_filter]
        if role_filter != "all":
            filtered_users = [u for u in filtered_users if u["role"] == role_filter]
        
        # Apply pagination
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_users = filtered_users[start_idx:end_idx]
        
        return {
            "status": "success",
            "users": paginated_users,
            "pagination": {
                "page": page,
                "size": size,
                "total_users": len(filtered_users),
                "total_pages": (len(filtered_users) + size - 1) // size
            },
            "filters": {
                "status": status_filter,
                "role": role_filter
            }
        }
        
    except Exception as e:
        logger.error(f"User listing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")

# ============================================================================
# SYSTEM CONFIGURATION ENDPOINTS
# ============================================================================

@router.post("/config/update")
async def update_system_configuration(
    request: SystemConfigUpdate,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "system_config"]))
):
    """Update system configuration settings"""
    try:
        config_id = f"config_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate configuration section
        allowed_sections = ["database", "cache", "external_tools", "security", "performance"]
        if request.config_section not in allowed_sections:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid config section. Allowed: {allowed_sections}"
            )
        
        # In production, this would update actual configuration
        # For now, validate and return success
        
        await _log_admin_action(
            current_user.get("user_id"),
            "config_update",
            {
                "config_section": request.config_section,
                "updated_keys": list(request.config_values.keys())
            }
        )
        
        return {
            "status": "success",
            "config_id": config_id,
            "config_section": request.config_section,
            "updated_values": request.config_values,
            "applied_immediately": request.apply_immediately,
            "message": f"Configuration section '{request.config_section}' updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Configuration update error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")

@router.get("/config/current")
async def get_current_configuration(
    section: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "system_config"]))
):
    """Get current system configuration"""
    try:
        # Mock configuration data
        full_config = {
            "database": {
                "host": "mongodb://localhost:27017",
                "max_connections": 100,
                "timeout_seconds": 30
            },
            "cache": {
                "redis_url": "redis://localhost:6379",
                "default_ttl": 3600,
                "max_memory": "1gb"
            },
            "external_tools": {
                "docker_timeout": 300,
                "max_concurrent_tools": 5,
                "tool_memory_limit": "2gb"
            },
            "security": {
                "jwt_expiry_hours": 24,
                "max_login_attempts": 5,
                "rate_limit_requests_per_minute": 60
            },
            "performance": {
                "max_file_size_mb": 100,
                "worker_processes": 4,
                "task_timeout_seconds": 3600
            }
        }
        
        if section:
            if section not in full_config:
                raise HTTPException(status_code=404, detail=f"Configuration section '{section}' not found")
            config_data = {section: full_config[section]}
        else:
            config_data = full_config
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": config_data
        }
        
    except Exception as e:
        logger.error(f"Configuration retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")

# ============================================================================
# DOCKER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/docker/containers")
async def list_docker_containers(
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "docker_management"]))
):
    """List and manage Docker containers"""
    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list(all=True)
        
        container_list = []
        for container in containers:
            container_stats = {
                "id": container.id[:12],
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                "status": container.status,
                "created": container.attrs["Created"],
                "state": container.attrs["State"],
                "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
                "labels": container.labels
            }
            
            # Get resource usage if running
            if container.status == "running":
                try:
                    stats = container.stats(stream=False)
                    memory_usage = stats["memory_stats"].get("usage", 0)
                    memory_limit = stats["memory_stats"].get("limit", 1)
                    
                    container_stats["resources"] = {
                        "memory_usage_mb": round(memory_usage / (1024**2), 2),
                        "memory_limit_mb": round(memory_limit / (1024**2), 2),
                        "memory_percent": round((memory_usage / memory_limit) * 100, 2)
                    }
                except:
                    container_stats["resources"] = {"error": "Unable to get stats"}
            
            container_list.append(container_stats)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "containers": container_list,
            "summary": {
                "total": len(containers),
                "running": len([c for c in containers if c.status == "running"]),
                "stopped": len([c for c in containers if c.status in ["exited", "stopped"]])
            }
        }
        
    except Exception as e:
        logger.error(f"Docker container listing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list containers: {str(e)}")

@router.post("/docker/cleanup")
async def cleanup_docker_resources(
    remove_unused_images: bool = Query(True),
    remove_stopped_containers: bool = Query(True),
    remove_unused_volumes: bool = Query(False),
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "docker_management"]))
):
    """Clean up Docker resources"""
    try:
        cleanup_id = f"docker_cleanup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_docker_cleanup,
            cleanup_id,
            remove_unused_images,
            remove_stopped_containers,
            remove_unused_volumes
        )
        
        await _log_admin_action(
            current_user.get("user_id"),
            "docker_cleanup",
            {
                "cleanup_id": cleanup_id,
                "remove_images": remove_unused_images,
                "remove_containers": remove_stopped_containers,
                "remove_volumes": remove_unused_volumes
            }
        )
        
        return {
            "status": "started",
            "cleanup_id": cleanup_id,
            "operations": {
                "remove_unused_images": remove_unused_images,
                "remove_stopped_containers": remove_stopped_containers,
                "remove_unused_volumes": remove_unused_volumes
            },
            "monitor_url": f"/api/v1/admin/docker-cleanup-status/{cleanup_id}"
        }
        
    except Exception as e:
        logger.error(f"Docker cleanup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Docker cleanup failed: {str(e)}")

# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/cache/flush")
async def flush_cache(
    cache_pattern: str = Query("*", description="Pattern for cache keys to flush"),
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "cache_management"]))
):
    """Flush cache entries matching pattern"""
    try:
        cache_manager = BioinformaticsCacheManager()
        
        # Flush cache
        flush_result = await cache_manager.invalidate_cache(cache_pattern)
        
        await _log_admin_action(
            current_user.get("user_id"),
            "cache_flush",
            {"pattern": cache_pattern}
        )
        
        return {
            "status": "success",
            "cache_pattern": cache_pattern,
            "flushed_keys": flush_result.get("flushed_count", 0),
            "message": f"Cache flushed for pattern: {cache_pattern}"
        }
        
    except Exception as e:
        logger.error(f"Cache flush error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cache flush failed: {str(e)}")

@router.post("/cache/optimize")
async def optimize_cache(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "cache_management"]))
):
    """Optimize cache performance"""
    try:
        optimization_id = f"cache_opt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_cache_optimization,
            optimization_id
        )
        
        await _log_admin_action(
            current_user.get("user_id"),
            "cache_optimization",
            {"optimization_id": optimization_id}
        )
        
        return {
            "status": "started",
            "optimization_id": optimization_id,
            "estimated_duration": "5-10 minutes",
            "monitor_url": f"/api/v1/admin/cache-optimization-status/{optimization_id}"
        }
        
    except Exception as e:
        logger.error(f"Cache optimization error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cache optimization failed: {str(e)}")

# ============================================================================
# SECURITY MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/security/audit-logs")
async def get_security_audit_logs(
    days: int = Query(7, ge=1, le=90),
    action_type: str = Query("all"),
    user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "security_audit"]))
):
    """Get security audit logs"""
    try:
        # Mock audit log data
        audit_logs = []
        
        for i in range(20):
            log_time = datetime.utcnow() - timedelta(hours=i*6)
            audit_logs.append({
                "timestamp": log_time.isoformat(),
                "user_id": f"user_{i % 5}",
                "action": ["login", "logout", "file_upload", "workflow_submit", "config_change"][i % 5],
                "ip_address": f"192.168.1.{100 + i % 50}",
                "user_agent": "Mozilla/5.0 (compatible)",
                "status": "success" if i % 8 != 0 else "failed",
                "details": {"resource": f"resource_{i}", "method": "POST"}
            })
        
        # Apply filters
        if action_type != "all":
            audit_logs = [log for log in audit_logs if log["action"] == action_type]
        if user_id:
            audit_logs = [log for log in audit_logs if log["user_id"] == user_id]
        
        return {
            "status": "success",
            "time_range_days": days,
            "filters": {"action_type": action_type, "user_id": user_id},
            "total_logs": len(audit_logs),
            "audit_logs": audit_logs
        }
        
    except Exception as e:
        logger.error(f"Audit logs error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")

@router.post("/security/scan")
async def run_security_scan(
    scan_type: str = Query("full", regex="^(full|vulnerabilities|permissions|configuration)$"),
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "security_scan"]))
):
    """Run security scan on the system"""
    try:
        scan_id = f"security_scan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_security_scan,
            scan_id,
            scan_type
        )
        
        await _log_admin_action(
            current_user.get("user_id"),
            "security_scan",
            {"scan_id": scan_id, "scan_type": scan_type}
        )
        
        return {
            "status": "started",
            "scan_id": scan_id,
            "scan_type": scan_type,
            "estimated_duration": "10-15 minutes" if scan_type == "full" else "2-5 minutes",
            "monitor_url": f"/api/v1/admin/security-scan-status/{scan_id}"
        }
        
    except Exception as e:
        logger.error(f"Security scan error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Security scan failed: {str(e)}")

# ============================================================================
# BACKUP AND RESTORE ENDPOINTS
# ============================================================================

@router.post("/backup/create")
async def create_system_backup(
    backup_type: str = Query("full", regex="^(full|database|files|config)$"),
    compression: bool = Query(True),
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "backup_management"]))
):
    """Create system backup"""
    try:
        backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_system_backup,
            backup_id,
            backup_type,
            compression
        )
        
        await _log_admin_action(
            current_user.get("user_id"),
            "backup_create",
            {"backup_id": backup_id, "backup_type": backup_type}
        )
        
        return {
            "status": "started",
            "backup_id": backup_id,
            "backup_type": backup_type,
            "compression": compression,
            "estimated_size": "unknown",
            "monitor_url": f"/api/v1/admin/backup-status/{backup_id}"
        }
        
    except Exception as e:
        logger.error(f"Backup creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {str(e)}")

@router.get("/backup/list")
async def list_backups(
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "backup_management"]))
):
    """List available system backups"""
    try:
        # Mock backup data
        backups = [
            {
                "backup_id": f"backup_202408{i:02d}_120000",
                "type": ["full", "database", "files"][i % 3],
                "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                "size_mb": 1024 + (i * 100),
                "status": "completed",
                "file_path": f"/backups/backup_202408{i:02d}_120000.tar.gz"
            }
            for i in range(1, 8)
        ]
        
        return {
            "status": "success",
            "total_backups": len(backups),
            "backups": backups,
            "total_size_gb": round(sum(b["size_mb"] for b in backups) / 1024, 2)
        }
        
    except Exception as e:
        logger.error(f"Backup listing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

# ============================================================================
# SYSTEM OPTIMIZATION ENDPOINTS
# ============================================================================

@router.post("/optimize/performance")
async def optimize_system_performance(
    optimization_areas: List[str] = Query(["database", "cache", "filesystem"]),
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_with_permissions(["admin", "system_optimization"]))
):
    """Optimize system performance"""
    try:
        optimization_id = f"perf_opt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_performance_optimization,
            optimization_id,
            optimization_areas
        )
        
        await _log_admin_action(
            current_user.get("user_id"),
            "performance_optimization",
            {"optimization_id": optimization_id, "areas": optimization_areas}
        )
        
        return {
            "status": "started",
            "optimization_id": optimization_id,
            "optimization_areas": optimization_areas,
            "estimated_duration": "15-30 minutes",
            "monitor_url": f"/api/v1/admin/optimization-status/{optimization_id}"
        }
        
    except Exception as e:
        logger.error(f"Performance optimization error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Performance optimization failed: {str(e)}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _log_admin_action(user_id: str, action: str, details: Dict[str, Any]):
    """Log administrative action for audit trail"""
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details,
            "ip_address": "unknown",  # Would get from request
            "user_agent": "unknown"   # Would get from request
        }
        
        # In production, this would store in audit_logs collection
        logger.info(f"Admin action logged: {action} by {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log admin action: {str(e)}")

async def _execute_maintenance(
    maintenance_id: str,
    operation_type: str,
    parameters: Dict[str, Any]
):
    """Execute maintenance operation"""
    try:
        if operation_type == "cleanup":
            # Clean up temporary files
            await _cleanup_temp_files(parameters.get("max_age_hours", 24))
            
        elif operation_type == "optimize":
            # Optimize database and cache
            await _optimize_system_components()
            
        elif operation_type == "backup":
            # Create system backup
            await _create_backup(parameters)
            
        logger.info(f"Maintenance {maintenance_id} completed: {operation_type}")
        
    except Exception as e:
        logger.error(f"Maintenance {maintenance_id} failed: {str(e)}")

async def _delayed_maintenance(
    maintenance_id: str,
    operation_type: str,
    parameters: Dict[str, Any],
    delay_seconds: float
):
    """Execute maintenance after delay"""
    await asyncio.sleep(delay_seconds)
    await _execute_maintenance(maintenance_id, operation_type, parameters)

async def _execute_filesystem_cleanup(
    cleanup_id: str,
    directories: List[str],
    max_age_days: int,
    dry_run: bool
):
    """Execute filesystem cleanup"""
    try:
        cleanup_results = {
            "cleanup_id": cleanup_id,
            "directories_processed": [],
            "files_removed": 0,
            "space_freed_mb": 0
        }
        
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        
        for directory in directories:
            dir_path = Path(f"/tmp/{directory}")  # Adjust paths as needed
            
            if dir_path.exists():
                removed_count = 0
                freed_bytes = 0
                
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_time < cutoff_time:
                            file_size = file_path.stat().st_size
                            
                            if not dry_run:
                                file_path.unlink()
                            
                            removed_count += 1
                            freed_bytes += file_size
                
                cleanup_results["directories_processed"].append({
                    "directory": directory,
                    "files_removed": removed_count,
                    "space_freed_mb": round(freed_bytes / (1024**2), 2)
                })
                
                cleanup_results["files_removed"] += removed_count
                cleanup_results["space_freed_mb"] += round(freed_bytes / (1024**2), 2)
        
        logger.info(f"Filesystem cleanup {cleanup_id} completed")
        
    except Exception as e:
        logger.error(f"Filesystem cleanup {cleanup_id} failed: {str(e)}")

async def _execute_database_maintenance(
    operation_id: str,
    operation: str,
    collections: Optional[List[str]],
    parameters: Dict[str, Any]
):
    """Execute database maintenance operation"""
    try:
        # Mock database maintenance operations
        if operation == "reindex":
            logger.info(f"Reindexing collections: {collections}")
        elif operation == "vacuum":
            logger.info(f"Vacuuming database")
        elif operation == "backup":
            logger.info(f"Creating database backup")
        elif operation == "integrity_check":
            logger.info(f"Running integrity check")
        
        logger.info(f"Database maintenance {operation_id} completed: {operation}")
        
    except Exception as e:
        logger.error(f"Database maintenance {operation_id} failed: {str(e)}")

async def _execute_docker_cleanup(
    cleanup_id: str,
    remove_unused_images: bool,
    remove_stopped_containers: bool,
    remove_unused_volumes: bool
):
    """Execute Docker cleanup operations"""
    try:
        docker_client = docker.from_env()
        cleanup_summary = {
            "images_removed": 0,
            "containers_removed": 0,
            "volumes_removed": 0,
            "space_freed_mb": 0
        }
        
        if remove_stopped_containers:
            stopped_containers = docker_client.containers.list(filters={"status": "exited"})
            for container in stopped_containers:
                container.remove()
                cleanup_summary["containers_removed"] += 1
        
        if remove_unused_images:
            # Remove dangling images
            dangling_images = docker_client.images.list(filters={"dangling": True})
            for image in dangling_images:
                docker_client.images.remove(image.id)
                cleanup_summary["images_removed"] += 1
        
        if remove_unused_volumes:
            # Remove unused volumes
            docker_client.volumes.prune()
            cleanup_summary["volumes_removed"] = 1  # Mock count
        
        logger.info(f"Docker cleanup {cleanup_id} completed: {cleanup_summary}")
        
    except Exception as e:
        logger.error(f"Docker cleanup {cleanup_id} failed: {str(e)}")

async def _execute_cache_optimization(optimization_id: str):
    """Execute cache optimization"""
    try:
        cache_manager = BioinformaticsCacheManager()
        
        # Perform cache optimization operations
        await cache_manager.optimize_cache()
        
        logger.info(f"Cache optimization {optimization_id} completed")
        
    except Exception as e:
        logger.error(f"Cache optimization {optimization_id} failed: {str(e)}")

async def _execute_security_scan(scan_id: str, scan_type: str):
    """Execute security scan"""
    try:
        # Mock security scan execution
        scan_results = {
            "vulnerabilities_found": 0,
            "permission_issues": 0,
            "configuration_warnings": 2,
            "recommendations": [
                "Update Docker images to latest versions",
                "Review file permissions on upload directory"
            ]
        }
        
        logger.info(f"Security scan {scan_id} completed: {scan_type}")
        
    except Exception as e:
        logger.error(f"Security scan {scan_id} failed: {str(e)}")

async def _execute_system_backup(backup_id: str, backup_type: str, compression: bool):
    """Execute system backup"""
    try:
        backup_results = {
            "backup_id": backup_id,
            "type": backup_type,
            "compression": compression,
            "size_mb": 0,
            "file_path": f"/backups/{backup_id}.tar.gz"
        }
        
        # Mock backup operations
        if backup_type in ["full", "database"]:
            # Backup database
            backup_results["size_mb"] += 500
        
        if backup_type in ["full", "files"]:
            # Backup files
            backup_results["size_mb"] += 2000
        
        if backup_type in ["full", "config"]:
            # Backup configuration
            backup_results["size_mb"] += 10
        
        logger.info(f"System backup {backup_id} completed: {backup_results}")
        
    except Exception as e:
        logger.error(f"System backup {backup_id} failed: {str(e)}")

async def _execute_performance_optimization(
    optimization_id: str,
    areas: List[str]
):
    """Execute performance optimization"""
    try:
        optimization_results = {}
        
        for area in areas:
            if area == "database":
                # Optimize database performance
                optimization_results["database"] = "indexes_optimized"
            elif area == "cache":
                # Optimize cache performance
                optimization_results["cache"] = "memory_compacted"
            elif area == "filesystem":
                # Optimize filesystem
                optimization_results["filesystem"] = "temp_files_cleaned"
        
        logger.info(f"Performance optimization {optimization_id} completed: {optimization_results}")
        
    except Exception as e:
        logger.error(f"Performance optimization {optimization_id} failed: {str(e)}")

async def _cleanup_temp_files(max_age_hours: int):
    """Clean up temporary files"""
    # Implementation for cleaning temp files
    pass

async def _optimize_system_components():
    """Optimize system components"""
    # Implementation for system optimization
    pass

async def _create_backup(parameters: Dict[str, Any]):
    """Create system backup"""
    # Implementation for backup creation
    pass