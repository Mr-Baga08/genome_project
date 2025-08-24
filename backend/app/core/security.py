# backend/app/core/security.py - Enhanced Security Implementation
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
from ..core.config import settings

class SecurityManager:
    """Enhanced security manager for production deployment"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
    
    def hash_password(self, password: str) -> str:
        """Hash password securely"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with expiration"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> dict:
        """Verify JWT token and return payload"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
            
            # Check if token is blacklisted
            if self.is_token_blacklisted(credentials.credentials):
                raise credentials_exception
                
            return payload
        except JWTError:
            raise credentials_exception
    
    def blacklist_token(self, token: str) -> None:
        """Add token to blacklist"""
        # Extract expiration from token
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            exp = payload.get("exp")
            if exp:
                # Store in Redis with expiration
                self.redis_client.set(f"blacklist:{token}", "1", ex=exp - int(datetime.utcnow().timestamp()))
        except JWTError:
            pass
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return bool(self.redis_client.get(f"blacklist:{token}"))
    
    def rate_limit_check(self, user_id: str, endpoint: str, limit: int = 100, window: int = 3600) -> bool:
        """Check rate limiting for user"""
        key = f"rate_limit:{user_id}:{endpoint}"
        current = self.redis_client.get(key)
        
        if current is None:
            self.redis_client.setex(key, window, 1)
            return True
        
        if int(current) >= limit:
            return False
        
        self.redis_client.incr(key)
        return True
    
    def audit_log(self, user_id: str, action: str, resource: str, success: bool, details: dict = None) -> None:
        """Log security events for audit"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "success": success,
            "details": details or {}
        }
        
        # Store in Redis and/or database for audit trail
        self.redis_client.lpush("security_audit_log", str(audit_entry))
        self.redis_client.ltrim("security_audit_log", 0, 10000)  # Keep last 10k entries

# Initialize security manager
security_manager = SecurityManager()
