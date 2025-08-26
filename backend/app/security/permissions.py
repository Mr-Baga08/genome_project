# backend/app/security/permissions.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
import jwt
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

# ============================================================================
# PERMISSIONS CONFIGURATION
# ============================================================================

PERMISSIONS = {
    "admin": [
        # System administration
        "admin",
        "system_maintenance",
        "system_config", 
        "user_management",
        "backup_management",
        "docker_management",
        "cache_management",
        "security_audit",
        "security_scan",
        "system_optimization",
        "database_admin",
        "file_management",
        "monitoring",
        
        # Data operations
        "read_sequences",
        "write_sequences", 
        "delete_sequences",
        "read_annotations",
        "write_annotations",
        "delete_annotations",
        
        # Analysis operations
        "run_analysis",
        "view_analysis_results",
        "delete_analysis_results",
        "run_assembly",
        "run_mapping",
        "run_variant_calling",
        "run_custom_scripts",
        
        # Workflow operations
        "create_workflows",
        "execute_workflows",
        "share_workflows",
        "delete_workflows",
        "create_custom_elements",
        
        # Advanced features
        "batch_operations",
        "parallel_processing",
        "external_tools",
        "api_access",
        "websocket_access"
    ],
    
    "power_user": [
        # Data operations
        "read_sequences",
        "write_sequences",
        "read_annotations", 
        "write_annotations",
        
        # Analysis operations
        "run_analysis",
        "view_analysis_results",
        "delete_own_analysis_results",
        "run_assembly",
        "run_mapping",
        "run_variant_calling",
        "run_custom_scripts",
        
        # Workflow operations
        "create_workflows",
        "execute_workflows",
        "share_workflows",
        "delete_own_workflows",
        "create_custom_elements",
        
        # Advanced features
        "batch_operations",
        "parallel_processing", 
        "external_tools",
        "api_access",
        "websocket_access",
        "monitoring"
    ],
    
    "user": [
        # Basic data operations
        "read_sequences",
        "write_sequences",
        "read_annotations",
        "write_annotations",
        
        # Basic analysis operations
        "run_analysis",
        "view_own_analysis_results",
        "delete_own_analysis_results",
        "run_assembly",
        "run_mapping",
        
        # Basic workflow operations
        "create_workflows",
        "execute_workflows", 
        "delete_own_workflows",
        
        # Limited features
        "api_access",
        "websocket_access"
    ],
    
    "viewer": [
        # Read-only operations
        "read_sequences",
        "read_annotations",
        "view_public_analysis_results",
        "view_public_workflows",
        
        # Limited API access
        "api_access"
    ],
    
    "guest": [
        # Very limited access
        "read_public_sequences",
        "view_public_workflows"
    ]
}

# Rate limiting configurations by role
RATE_LIMITS = {
    "admin": {
        "requests_per_minute": 1000,
        "concurrent_operations": 50,
        "file_upload_mb_per_hour": 10000
    },
    "power_user": {
        "requests_per_minute": 500,
        "concurrent_operations": 20,
        "file_upload_mb_per_hour": 5000
    },
    "user": {
        "requests_per_minute": 100,
        "concurrent_operations": 5,
        "file_upload_mb_per_hour": 1000
    },
    "viewer": {
        "requests_per_minute": 50,
        "concurrent_operations": 2,
        "file_upload_mb_per_hour": 100
    },
    "guest": {
        "requests_per_minute": 10,
        "concurrent_operations": 1,
        "file_upload_mb_per_hour": 0
    }
}

# JWT Configuration
JWT_SECRET_KEY = "your-secret-key-here"  # Should come from environment
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# ============================================================================
# JWT TOKEN HANDLING
# ============================================================================

def create_access_token(user_data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    try:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        payload = {
            "user_id": user_data["user_id"],
            "email": user_data.get("email"),
            "role": user_data.get("role", "user"),
            "permissions": PERMISSIONS.get(user_data.get("role", "user"), []),
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "ugene-platform"
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
        
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )

def verify_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT access token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Check if token is expired
        exp_timestamp = payload.get("exp")
        if exp_timestamp and datetime.utcfromtimestamp(exp_timestamp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )

# ============================================================================
# PERMISSION CHECKING FUNCTIONS
# ============================================================================

def check_user_permissions(user_permissions: List[str], required_permissions: List[str]) -> bool:
    """Check if user has all required permissions"""
    return all(permission in user_permissions for permission in required_permissions)

def get_user_rate_limits(user_role: str) -> Dict[str, Any]:
    """Get rate limits for user role"""
    return RATE_LIMITS.get(user_role, RATE_LIMITS["guest"])

# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    try:
        token = credentials.credentials
        payload = verify_access_token(token)
        
        # Add rate limiting info
        user_role = payload.get("role", "user")
        payload["rate_limits"] = get_user_rate_limits(user_role)
        
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

def get_current_user_with_permissions(required_permissions: List[str]):
    """Dependency factory for checking specific permissions"""
    
    async def check_permissions(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        
        if not check_user_permissions(user_permissions, required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permissions}"
            )
        
        return current_user
    
    return check_permissions

async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency for admin-only endpoints"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_authenticated_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency for any authenticated user"""
    return current_user

# ============================================================================
# ROLE-BASED ACCESS DECORATORS
# ============================================================================

def require_permissions(permissions: List[str]):
    """Decorator for functions requiring specific permissions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would typically be used with FastAPI dependencies
            # The actual permission checking is done in the dependency
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: str):
    """Decorator for functions requiring specific role"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would typically be used with FastAPI dependencies
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# ============================================================================
# PERMISSION UTILITIES
# ============================================================================

class PermissionManager:
    """Utility class for permission management"""
    
    @staticmethod
    def get_all_permissions() -> Dict[str, List[str]]:
        """Get all defined permissions by role"""
        return PERMISSIONS.copy()
    
    @staticmethod
    def get_role_permissions(role: str) -> List[str]:
        """Get permissions for a specific role"""
        return PERMISSIONS.get(role, [])
    
    @staticmethod
    def has_permission(user_role: str, permission: str) -> bool:
        """Check if role has specific permission"""
        role_permissions = PERMISSIONS.get(user_role, [])
        return permission in role_permissions
    
    @staticmethod
    def can_access_resource(user_role: str, resource_type: str, action: str) -> bool:
        """Check if user can perform action on resource type"""
        permission_name = f"{action}_{resource_type}"
        return PermissionManager.has_permission(user_role, permission_name)
    
    @staticmethod
    def get_accessible_resources(user_role: str) -> Dict[str, List[str]]:
        """Get all resources accessible to a role"""
        role_permissions = PERMISSIONS.get(user_role, [])
        
        resources = {}
        for permission in role_permissions:
            if '_' in permission:
                action, resource = permission.split('_', 1)
                if resource not in resources:
                    resources[resource] = []
                resources[resource].append(action)
        
        return resources

# ============================================================================
# SECURITY MIDDLEWARE HELPERS
# ============================================================================

class SecurityContext:
    """Security context for request processing"""
    
    def __init__(self, user: Dict[str, Any]):
        self.user = user
        self.user_id = user.get("user_id")
        self.role = user.get("role", "guest")
        self.permissions = user.get("permissions", [])
        self.rate_limits = user.get("rate_limits", RATE_LIMITS["guest"])
    
    def can(self, permission: str) -> bool:
        """Check if user has permission"""
        return permission in self.permissions
    
    def can_access(self, resource_type: str, action: str) -> bool:
        """Check if user can perform action on resource"""
        return PermissionManager.can_access_resource(self.role, resource_type, action)
    
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == "admin"
    
    def is_power_user(self) -> bool:
        """Check if user is power user or admin"""
        return self.role in ["admin", "power_user"]
    
    def owns_resource(self, resource: Dict[str, Any]) -> bool:
        """Check if user owns the resource"""
        resource_owner = resource.get("created_by") or resource.get("user_id") or resource.get("owner_id")
        return resource_owner == self.user_id

# ============================================================================
# INITIALIZATION FUNCTION
# ============================================================================

async def init_permissions():
    """Initialize permission system"""
    try:
        # Validate permission definitions
        all_permissions = set()
        for role, perms in PERMISSIONS.items():
            all_permissions.update(perms)
        
        logger.info(f"Permission system initialized with {len(all_permissions)} unique permissions across {len(PERMISSIONS)} roles")
        
        # Log permission matrix for debugging
        for role, perms in PERMISSIONS.items():
            logger.debug(f"Role '{role}': {len(perms)} permissions")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize permissions: {str(e)}")
        return False

# ============================================================================
# RESOURCE OWNERSHIP UTILITIES
# ============================================================================

async def check_resource_ownership(
    user: Dict[str, Any],
    resource_type: str,
    resource_id: str,
    db_manager
) -> bool:
    """Check if user owns a specific resource"""
    try:
        collection_map = {
            "sequence": "sequences",
            "analysis": "analysis_results", 
            "workflow": "workflows",
            "motif": "custom_motifs",
            "element": "custom_elements"
        }
        
        collection_name = collection_map.get(resource_type)
        if not collection_name:
            return False
        
        collection = await db_manager.get_collection(collection_name)
        resource = await collection.find_one({"_id": resource_id})
        
        if not resource:
            return False
        
        # Check ownership
        resource_owner = (
            resource.get("created_by") or 
            resource.get("user_id") or 
            resource.get("owner_id")
        )
        
        return resource_owner == user.get("user_id")
        
    except Exception as e:
        logger.error(f"Error checking resource ownership: {str(e)}")
        return False

# ============================================================================
# PERMISSION-BASED QUERY FILTERS
# ============================================================================

def get_user_data_filter(user: Dict[str, Any]) -> Dict[str, Any]:
    """Get MongoDB filter for user's accessible data"""
    user_id = user.get("user_id")
    role = user.get("role", "guest")
    
    if role == "admin":
        # Admin can see everything
        return {}
    elif role in ["power_user", "user"]:
        # Users can see their own data + public data
        return {
            "$or": [
                {"created_by": user_id},
                {"user_id": user_id},
                {"is_public": True}
            ]
        }
    else:
        # Viewers and guests can only see public data
        return {"is_public": True}

def apply_user_permissions_to_query(query: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Apply user permissions to database query"""
    user_filter = get_user_data_filter(user)
    
    if user_filter:
        if query:
            # Combine existing query with user filter
            return {"$and": [query, user_filter]}
        else:
            return user_filter
    
    return query

# ============================================================================
# AUDIT LOGGING HELPERS
# ============================================================================

async def log_permission_check(
    user_id: str,
    required_permissions: List[str],
    granted: bool,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None
):
    """Log permission checks for audit trail"""
    try:
        # This would integrate with your audit logging system
        audit_data = {
            "event_type": "permission_check",
            "user_id": user_id,
            "required_permissions": required_permissions,
            "granted": granted,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Permission check: {user_id} - {required_permissions} - {'GRANTED' if granted else 'DENIED'}")
        
    except Exception as e:
        logger.error(f"Error logging permission check: {str(e)}")

# ============================================================================
# ENHANCED DEPENDENCY FUNCTIONS
# ============================================================================

def get_current_user_with_resource_access(resource_type: str, action: str = "read"):
    """Dependency for checking resource-specific access"""
    
    async def check_resource_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        required_permission = f"{action}_{resource_type}"
        user_permissions = current_user.get("permissions", [])
        
        if required_permission not in user_permissions:
            await log_permission_check(
                current_user.get("user_id"),
                [required_permission],
                False,
                resource_type
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission}"
            )
        
        await log_permission_check(
            current_user.get("user_id"),
            [required_permission], 
            True,
            resource_type
        )
        
        return current_user
    
    return check_resource_access

def get_current_user_with_ownership_check(resource_type: str):
    """Dependency for checking resource ownership"""
    
    async def check_ownership(
        resource_id: str,
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        # Admin can access any resource
        if current_user.get("role") == "admin":
            return current_user
        
        # Check ownership for non-admin users
        from ..database.database_setup import DatabaseManager
        db_manager = DatabaseManager()
        
        has_ownership = await check_resource_ownership(
            current_user, resource_type, resource_id, db_manager
        )
        
        if not has_ownership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this resource"
            )
        
        return current_user
    
    return check_ownership

# ============================================================================
# ROLE VALIDATION
# ============================================================================

def validate_role_hierarchy(current_role: str, target_role: str) -> bool:
    """Validate if current role can manage target role"""
    role_hierarchy = {
        "admin": 4,
        "power_user": 3,
        "user": 2,
        "viewer": 1,
        "guest": 0
    }
    
    current_level = role_hierarchy.get(current_role, 0)
    target_level = role_hierarchy.get(target_role, 0)
    
    return current_level > target_level

# ============================================================================
# SECURITY UTILITIES
# ============================================================================

class SecurityUtils:
    """Utility functions for security operations"""
    
    @staticmethod
    def mask_sensitive_data(data: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Mask sensitive data based on user role"""
        if user_role == "admin":
            return data  # Admin sees everything
        
        # Create copy to avoid modifying original
        masked_data = data.copy()
        
        # Remove sensitive fields for non-admin users
        sensitive_fields = ["password", "secret_key", "api_key", "private_key"]
        for field in sensitive_fields:
            if field in masked_data:
                masked_data[field] = "***MASKED***"
        
        # Mask IP addresses for viewers and guests
        if user_role in ["viewer", "guest"]:
            if "ip_address" in masked_data:
                ip_parts = masked_data["ip_address"].split(".")
                if len(ip_parts) == 4:
                    masked_data["ip_address"] = f"{ip_parts[0]}.{ip_parts[1]}.*.* "
        
        return masked_data
    
    @staticmethod
    def generate_api_key(user_id: str, permissions: List[str]) -> str:
        """Generate API key for programmatic access"""
        try:
            api_key_data = {
                "user_id": user_id,
                "permissions": permissions,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                "key_type": "api"
            }
            
            api_key = jwt.encode(api_key_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            return api_key
            
        except Exception as e:
            logger.error(f"Error generating API key: {str(e)}")
            raise e
    
    @staticmethod
    def verify_api_key(api_key: str) -> Dict[str, Any]:
        """Verify API key"""
        try:
            payload = jwt.decode(api_key, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Check expiration
            exp_str = payload.get("expires_at")
            if exp_str:
                exp_date = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                if exp_date < datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="API key has expired"
                    )
            
            return payload
            
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid API key: {str(e)}"
            )

# ============================================================================
# PERMISSION CHECKING FOR SPECIFIC OPERATIONS
# ============================================================================

class OperationPermissions:
    """Permission checks for specific operations"""
    
    @staticmethod
    def can_run_external_tools(user_role: str) -> bool:
        """Check if user can run external bioinformatics tools"""
        return "external_tools" in PERMISSIONS.get(user_role, [])
    
    @staticmethod
    def can_use_custom_scripts(user_role: str) -> bool:
        """Check if user can execute custom scripts"""
        return "run_custom_scripts" in PERMISSIONS.get(user_role, [])
    
    @staticmethod
    def can_access_system_admin(user_role: str) -> bool:
        """Check if user can access system administration"""
        return user_role == "admin"
    
    @staticmethod
    def can_manage_users(user_role: str) -> bool:
        """Check if user can manage other users"""
        return "user_management" in PERMISSIONS.get(user_role, [])
    
    @staticmethod
    def can_view_audit_logs(user_role: str) -> bool:
        """Check if user can view audit logs"""
        return "security_audit" in PERMISSIONS.get(user_role, [])
    
    @staticmethod
    def get_max_file_size(user_role: str) -> int:
        """Get maximum file size user can upload (in MB)"""
        limits = RATE_LIMITS.get(user_role, RATE_LIMITS["guest"])
        return limits.get("file_upload_mb_per_hour", 100)
    
    @staticmethod
    def get_max_concurrent_operations(user_role: str) -> int:
        """Get maximum concurrent operations for user"""
        limits = RATE_LIMITS.get(user_role, RATE_LIMITS["guest"])
        return limits.get("concurrent_operations", 1)

# ============================================================================
# EXAMPLE USAGE IN ENDPOINTS
# ============================================================================

"""
Example usage in FastAPI endpoints:

@router.post("/sequences/create")
async def create_sequence(
    sequence_data: dict,
    current_user: dict = Depends(get_current_user_with_permissions(["write_sequences"]))
):
    # User has write_sequences permission
    pass

@router.delete("/analysis/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user_with_ownership_check("analysis"))
):
    # User owns the analysis or is admin
    pass

@router.get("/admin/users")
async def list_users(
    current_user: dict = Depends(get_admin_user)
):
    # Only admin users can access this
    pass
"""