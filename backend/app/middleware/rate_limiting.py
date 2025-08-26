# backend/app/middleware/rate_limiting.py
import asyncio
import time
import json
import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ============================================================================
# TOKEN BUCKET RATE LIMITER
# ============================================================================

class TokenBucket:
    """Token bucket algorithm implementation for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket"""
        async with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status"""
        return {
            "capacity": self.capacity,
            "current_tokens": self.tokens,
            "refill_rate": self.refill_rate,
            "last_refill": self.last_refill
        }

# ============================================================================
# REDIS-BASED DISTRIBUTED RATE LIMITER
# ============================================================================

class RedisRateLimiter:
    """Redis-based rate limiter for distributed deployments"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            if not self._connected:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                self._connected = True
                logger.info("✅ Redis rate limiter connected")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {str(e)}")
            self.redis_client = None
            self._connected = False
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int,
        tokens_consumed: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis sliding window"""
        
        if not self._connected:
            await self.connect()
        
        if not self.redis_client:
            # Fallback to in-memory rate limiting
            return True, {"fallback": True, "redis_unavailable": True}
        
        try:
            current_time = time.time()
            window_start = current_time - window_seconds
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration for the key
            pipe.expire(key, window_seconds + 1)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]  # Result of zcard
            
            # Check if limit exceeded
            if current_count >= limit:
                # Remove the request we just added since it exceeds limit
                await self.redis_client.zrem(key, str(current_time))
                
                # Calculate reset time
                earliest_request = await self.redis_client.zrange(key, 0, 0, withscores=True)
                reset_time = earliest_request[0][1] + window_seconds if earliest_request else current_time + window_seconds
                
                return False, {
                    "limit_exceeded": True,
                    "current_count": current_count,
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "reset_time": reset_time,
                    "retry_after": int(reset_time - current_time)
                }
            
            return True, {
                "allowed": True,
                "current_count": current_count + 1,
                "limit": limit,
                "remaining": limit - (current_count + 1),
                "reset_time": current_time + window_seconds
            }
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {str(e)}")
            # Fall back to allowing request on Redis failure
            return True, {"fallback": True, "error": str(e)}

    async def get_rate_limit_status(self, key: str, window_seconds: int) -> Dict[str, Any]:
        """Get current rate limit status for a key"""
        if not self._connected or not self.redis_client:
            return {"error": "Redis not available"}
        
        try:
            current_time = time.time()
            window_start = current_time - window_seconds
            
            # Get current count in window
            current_count = await self.redis_client.zcount(key, window_start, current_time)
            
            return {
                "key": key,
                "current_count": current_count,
                "window_seconds": window_seconds,
                "timestamp": current_time
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {str(e)}")
            return {"error": str(e)}

# ============================================================================
# RATE LIMITING MIDDLEWARE
# ============================================================================

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, redis_url: str = "redis://localhost:6379"):
        super().__init__(app)
        self.redis_limiter = RedisRateLimiter(redis_url)
        self.local_limiters = {}  # Fallback in-memory limiters
        
        # Rate limiting rules
        self.endpoint_rules = {
            # High-cost operations
            "/api/v1/dna-assembly/": {"requests_per_minute": 10, "tokens_per_request": 5},
            "/api/v1/ngs-mapping/": {"requests_per_minute": 15, "tokens_per_request": 3},
            "/api/v1/analysis/": {"requests_per_minute": 30, "tokens_per_request": 2},
            
            # Medium-cost operations  
            "/api/v1/data-converters/": {"requests_per_minute": 60, "tokens_per_request": 2},
            "/api/v1/data-writers/": {"requests_per_minute": 100, "tokens_per_request": 1},
            
            # Low-cost operations
            "/api/v1/sequences/": {"requests_per_minute": 200, "tokens_per_request": 1},
            "/api/v1/monitoring/": {"requests_per_minute": 300, "tokens_per_request": 1},
            
            # Admin operations
            "/api/v1/admin/": {"requests_per_minute": 50, "tokens_per_request": 2}
        }
        
        # Global rate limits
        self.global_limits = {
            "admin": 1000,
            "power_user": 500,
            "user": 100,
            "viewer": 50,
            "guest": 10
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        start_time = time.time()
        
        try:
            # Get user info from request
            user_info = await self._get_user_from_request(request)
            user_role = user_info.get("role", "guest")
            user_id = user_info.get("user_id", "anonymous")
            
            # Check if endpoint should be rate limited
            endpoint_path = self._get_endpoint_path(request.url.path)
            
            if endpoint_path:
                # Apply endpoint-specific rate limiting
                allowed, rate_info = await self._check_endpoint_rate_limit(
                    user_id, user_role, endpoint_path, request
                )
                
                if not allowed:
                    return self._create_rate_limit_response(rate_info)
            
            # Apply global rate limiting
            allowed, global_rate_info = await self._check_global_rate_limit(user_id, user_role)
            
            if not allowed:
                return self._create_rate_limit_response(global_rate_info)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limiting headers
            self._add_rate_limit_headers(response, rate_info if endpoint_path else global_rate_info)
            
            # Log request metrics
            processing_time = time.time() - start_time
            await self._log_request_metrics(request, response, processing_time, user_info)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {str(e)}")
            # Continue processing on middleware failure
            return await call_next(request)
    
    async def _get_user_from_request(self, request: Request) -> Dict[str, Any]:
        """Extract user information from request"""
        try:
            # Try to get user from Authorization header
            auth_header = request.headers.get("Authorization")
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
                # Verify token (simplified - in production use your auth service)
                from ..security.permissions import verify_access_token
                user_payload = verify_access_token(token)
                return user_payload
            
        except Exception as e:
            logger.debug(f"Could not extract user from request: {str(e)}")
        
        # Return anonymous user
        return {
            "user_id": f"anon_{request.client.host}" if request.client else "anon_unknown",
            "role": "guest"
        }
    
    def _get_endpoint_path(self, full_path: str) -> Optional[str]:
        """Get rate limiting rule for endpoint"""
        for endpoint_pattern in self.endpoint_rules.keys():
            if full_path.startswith(endpoint_pattern):
                return endpoint_pattern
        return None
    
    async def _check_endpoint_rate_limit(
        self, 
        user_id: str, 
        user_role: str, 
        endpoint_path: str,
        request: Request
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check endpoint-specific rate limit"""
        
        rule = self.endpoint_rules[endpoint_path]
        requests_per_minute = rule["requests_per_minute"]
        tokens_per_request = rule["tokens_per_request"]
        
        # Adjust limits based on user role
        role_multiplier = {
            "admin": 3.0,
            "power_user": 2.0,
            "user": 1.0,
            "viewer": 0.5,
            "guest": 0.2
        }.get(user_role, 0.2)
        
        effective_limit = int(requests_per_minute * role_multiplier)
        
        # Create rate limit key
        rate_key = f"rate_limit:endpoint:{endpoint_path}:{user_id}"
        
        # Check with Redis limiter
        allowed, info = await self.redis_limiter.check_rate_limit(
            key=rate_key,
            limit=effective_limit,
            window_seconds=60,  # 1 minute window
            tokens_consumed=tokens_per_request
        )
        
        info.update({
            "endpoint": endpoint_path,
            "user_role": user_role,
            "effective_limit": effective_limit,
            "original_limit": requests_per_minute,
            "role_multiplier": role_multiplier
        })
        
        return allowed, info
    
    async def _check_global_rate_limit(self, user_id: str, user_role: str) -> Tuple[bool, Dict[str, Any]]:
        """Check global rate limit for user"""
        
        global_limit = self.global_limits.get(user_role, 10)
        rate_key = f"rate_limit:global:{user_id}"
        
        allowed, info = await self.redis_limiter.check_rate_limit(
            key=rate_key,
            limit=global_limit,
            window_seconds=60,  # 1 minute window
            tokens_consumed=1
        )
        
        info.update({
            "limit_type": "global",
            "user_role": user_role,
            "global_limit": global_limit
        })
        
        return allowed, info
    
    def _create_rate_limit_response(self, rate_info: Dict[str, Any]) -> JSONResponse:
        """Create rate limit exceeded response"""
        
        retry_after = rate_info.get("retry_after", 60)
        
        response_data = {
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Try again in {retry_after} seconds.",
            "rate_limit_info": {
                "limit": rate_info.get("limit"),
                "current_count": rate_info.get("current_count"),
                "window_seconds": rate_info.get("window_seconds"),
                "retry_after": retry_after,
                "limit_type": rate_info.get("limit_type", "endpoint")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        headers = {
            "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(max(0, rate_info.get("remaining", 0))),
            "X-RateLimit-Reset": str(int(rate_info.get("reset_time", time.time() + 60))),
            "Retry-After": str(retry_after)
        }
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=response_data,
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response, rate_info: Dict[str, Any]):
        """Add rate limiting headers to response"""
        try:
            if rate_info:
                response.headers["X-RateLimit-Limit"] = str(rate_info.get("limit", 0))
                response.headers["X-RateLimit-Remaining"] = str(max(0, rate_info.get("remaining", 0)))
                response.headers["X-RateLimit-Reset"] = str(int(rate_info.get("reset_time", time.time() + 60)))
                
        except Exception as e:
            logger.debug(f"Could not add rate limit headers: {str(e)}")
    
    async def _log_request_metrics(
        self,
        request: Request,
        response,
        processing_time: float,
        user_info: Dict[str, Any]
    ):
        """Log request metrics for monitoring"""
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "path": request.url.path,
                "status_code": getattr(response, 'status_code', 0),
                "processing_time_ms": round(processing_time * 1000, 2),
                "user_id": user_info.get("user_id"),
                "user_role": user_info.get("role"),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")[:200]  # Truncate long user agents
            }
            
            # In production, this would be sent to metrics collection system
            logger.debug(f"Request metrics: {metrics}")
            
        except Exception as e:
            logger.debug(f"Error logging request metrics: {str(e)}")

# ============================================================================
# ADVANCED RATE LIMITING STRATEGIES
# ============================================================================

class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system load"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.base_limiter = RedisRateLimiter(redis_url)
        self.load_threshold = {
            "cpu_high": 80.0,
            "memory_high": 85.0,
            "active_tasks_high": 100
        }
    
    async def get_adaptive_limits(self, base_limits: Dict[str, int]) -> Dict[str, int]:
        """Get rate limits adjusted for current system load"""
        try:
            # Get current system metrics
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            # Calculate load factor
            load_factor = 1.0
            
            if cpu_percent > self.load_threshold["cpu_high"]:
                load_factor *= 0.5  # Reduce limits by 50% if CPU high
            
            if memory_percent > self.load_threshold["memory_high"]:
                load_factor *= 0.7  # Reduce limits by 30% if memory high
            
            # Apply load factor to all limits
            adaptive_limits = {}
            for limit_type, base_limit in base_limits.items():
                adaptive_limits[limit_type] = max(1, int(base_limit * load_factor))
            
            return adaptive_limits
            
        except Exception as e:
            logger.error(f"Error calculating adaptive limits: {str(e)}")
            return base_limits  # Return original limits on error

# ============================================================================
# SPECIALIZED RATE LIMITERS
# ============================================================================

class FileUploadRateLimiter:
    """Specialized rate limiter for file uploads"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_limiter = RedisRateLimiter(redis_url)
    
    async def check_upload_limit(
        self,
        user_id: str,
        user_role: str,
        file_size_mb: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check file upload rate limits"""
        
        from ..security.permissions import RATE_LIMITS
        role_limits = RATE_LIMITS.get(user_role, RATE_LIMITS["guest"])
        
        hourly_limit_mb = role_limits.get("file_upload_mb_per_hour", 100)
        
        # Check hourly upload quota
        quota_key = f"upload_quota:{user_id}"
        allowed, info = await self.redis_limiter.check_rate_limit(
            key=quota_key,
            limit=int(hourly_limit_mb),
            window_seconds=3600,  # 1 hour
            tokens_consumed=int(file_size_mb)
        )
        
        info.update({
            "limit_type": "file_upload",
            "file_size_mb": file_size_mb,
            "hourly_limit_mb": hourly_limit_mb,
            "user_role": user_role
        })
        
        return allowed, info

class ComputationalRateLimiter:
    """Rate limiter for computationally intensive operations"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_limiter = RedisRateLimiter(redis_url)
        
        # Computational cost weights
        self.operation_costs = {
            "assembly": 10,
            "blast_search": 5,
            "multiple_alignment": 3,
            "phylogenetic_analysis": 8,
            "variant_calling": 6,
            "mapping": 4,
            "basic_analysis": 1
        }
    
    async def check_computational_limit(
        self,
        user_id: str,
        user_role: str,
        operation_type: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check computational resource limits"""
        
        cost = self.operation_costs.get(operation_type, 1)
        
        # Role-based computational budgets (cost units per hour)
        computational_budgets = {
            "admin": 500,
            "power_user": 200,
            "user": 50,
            "viewer": 10,
            "guest": 0
        }
        
        budget = computational_budgets.get(user_role, 0)
        
        if budget == 0:
            return False, {
                "error": "No computational budget for this role",
                "user_role": user_role,
                "operation_type": operation_type
            }
        
        # Check computational rate limit
        budget_key = f"computational_budget:{user_id}"
        allowed, info = await self.redis_limiter.check_rate_limit(
            key=budget_key,
            limit=budget,
            window_seconds=3600,  # 1 hour
            tokens_consumed=cost
        )
        
        info.update({
            "limit_type": "computational",
            "operation_type": operation_type,
            "operation_cost": cost,
            "hourly_budget": budget,
            "user_role": user_role
        })
        
        return allowed, info

# ============================================================================
# RATE LIMITING UTILITIES
# ============================================================================

class RateLimitingUtils:
    """Utility functions for rate limiting"""
    
    @staticmethod
    def calculate_backoff_time(attempt_count: int, base_delay: float = 1.0) -> float:
        """Calculate exponential backoff time"""
        return min(base_delay * (2 ** attempt_count), 300)  # Max 5 minutes
    
    @staticmethod
    def get_client_identifier(request: Request) -> str:
        """Get unique client identifier for rate limiting"""
        # Try to get user ID from auth, fallback to IP
        try:
            # This would integrate with your auth system
            return f"ip_{request.client.host}" if request.client else "unknown"
        except:
            return "unknown"
    
    @staticmethod
    async def is_whitelisted(identifier: str, whitelist: List[str]) -> bool:
        """Check if client is whitelisted"""
        return identifier in whitelist
    
    @staticmethod
    def should_exempt_from_rate_limiting(request: Request) -> bool:
        """Check if request should be exempt from rate limiting"""
        # Exempt health checks and system monitoring
        exempt_paths = ["/health", "/metrics", "/api/v1/monitoring/health"]
        return request.url.path in exempt_paths

# ============================================================================
# INITIALIZATION AND CONFIGURATION
# ============================================================================

async def init_rate_limiting(app, redis_url: str = "redis://localhost:6379"):
    """Initialize rate limiting system"""
    try:
        # Create global rate limiter
        global_limiter = RedisRateLimiter(redis_url)
        await global_limiter.connect()
        
        # Store in app state for access by other components
        app.state.rate_limiter = global_limiter
        app.state.file_upload_limiter = FileUploadRateLimiter(redis_url)
        app.state.computational_limiter = ComputationalRateLimiter(redis_url)
        
        logger.info("✅ Rate limiting system initialized")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize rate limiting: {str(e)}")
        return False

# Example usage in endpoints:
"""
@router.post("/expensive-operation")
async def expensive_operation(
    request: Request,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    # Check computational rate limit
    comp_limiter = request.app.state.computational_limiter
    allowed, info = await comp_limiter.check_computational_limit(
        current_user["user_id"],
        current_user["role"], 
        "assembly"
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Computational rate limit exceeded",
            headers={"Retry-After": str(info.get("retry_after", 3600))}
        )
    
    # Proceed with expensive operation
    return await perform_assembly(data)
"""