# backend/app/security/security_manager.py
import jwt
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from functools import wraps
import logging
import re
import os

logger = logging.getLogger(__name__)

@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    max_file_size_mb: int = 500
    allowed_file_types: List[str] = None
    max_sequences_per_request: int = 10000
    rate_limit_requests_per_minute: int = 100
    session_timeout_hours: int = 24
    require_2fa: bool = False
    audit_log_retention_days: int = 90

@dataclass
class UserSession:
    """User session data"""
    user_id: str
    username: str
    email: str
    permissions: List[str]
    organization: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str

class BiologicalDataSecurity:
    """Comprehensive security manager for biological data"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        self.algorithm = 'HS256'
        
        # Security policies
        self.security_policy = SecurityPolicy(
            allowed_file_types=['fasta', 'fastq', 'gff', 'gtf', 'bed', 'vcf', 'sam', 'bam', 'csv', 'tsv']
        )
        
        # Active sessions
        self.active_sessions = {}
        
        # Rate limiting storage
        self.rate_limit_storage = {}
        
        # Audit log
        self.audit_log = []
        
        # Sensitive data patterns
        self.sensitive_patterns = [
            r'password',
            r'secret',
            r'key',
            r'token',
            r'private',
            r'confidential'
        ]
    
    def create_access_token(self, user_data: Dict, expires_delta: timedelta = None) -> str:
        """Create JWT access token"""
        
        try:
            if expires_delta is None:
                expires_delta = timedelta(hours=self.security_policy.session_timeout_hours)
            
            expire = datetime.utcnow() + expires_delta
            
            # Token payload
            payload = {
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'email': user_data.get('email', ''),
                'permissions': user_data.get('permissions', []),
                'organization': user_data.get('organization', ''),
                'exp': expire,
                'iat': datetime.utcnow(),
                'token_type': 'access'
            }
            
            # Create token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Create session
            session = UserSession(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data.get('email', ''),
                permissions=user_data.get('permissions', []),
                organization=user_data.get('organization', ''),
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                ip_address=user_data.get('ip_address', ''),
                user_agent=user_data.get('user_agent', '')
            )
            
            self.active_sessions[user_data['user_id']] = session
            
            # Log token creation
            self._audit_log('token_created', user_data['user_id'], {
                'username': user_data['username'],
                'expires_at': expire.isoformat()
            })
            
            return token
            
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise SecurityException("Failed to create access token")
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if user session exists and is active
            user_id = payload['user_id']
            if user_id in self.active_sessions:
                session = self.active_sessions[user_id]
                
                # Update last activity
                session.last_activity = datetime.utcnow()
                
                # Check session timeout
                if (datetime.utcnow() - session.created_at).total_seconds() > (self.security_policy.session_timeout_hours * 3600):
                    self._invalidate_session(user_id)
                    raise SecurityException("Session expired")
                
                return {
                    'valid': True,
                    'payload': payload,
                    'session': session
                }
            else:
                raise SecurityException("Session not found")
                
        except jwt.ExpiredSignatureError:
            raise SecurityException("Token expired")
        except jwt.InvalidTokenError:
            raise SecurityException("Invalid token")
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise SecurityException("Token verification failed")
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        
        # Validate password strength
        if not self._validate_password_strength(password):
            raise SecurityException("Password does not meet security requirements")
        
        # Generate salt and hash
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False
    
    def _validate_password_strength(self, password: str) -> bool:
        """Validate password meets security requirements"""
        
        if len(password) < 12:
            return False
        
        # Check for different character types
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        return has_lower and has_upper and has_digit and has_special
    
    def validate_biological_data(self, data: Any, data_type: str) -> Dict:
        """Validate biological data for security and integrity"""
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_flags": []
        }
        
        try:
            if data_type == 'sequence':
                validation_result.update(self._validate_sequence_data(data))
            elif data_type == 'file_upload':
                validation_result.update(self._validate_file_upload(data))
            elif data_type == 'user_input':
                validation_result.update(self._validate_user_input(data))
            else:
                validation_result["errors"].append(f"Unknown data type: {data_type}")
                validation_result["valid"] = False
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating biological data: {str(e)}")
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation failed: {str(e)}")
            return validation_result
    
    def _validate_sequence_data(self, sequence_data: Any) -> Dict:
        """Validate sequence data for security issues"""
        
        result = {"valid": True, "errors": [], "warnings": [], "security_flags": []}
        
        if isinstance(sequence_data, str):
            sequences = [sequence_data]
        elif isinstance(sequence_data, list):
            sequences = sequence_data
        elif isinstance(sequence_data, dict) and 'sequence' in sequence_data:
            sequences = [sequence_data['sequence']]
        else:
            result["errors"].append("Invalid sequence data format")
            result["valid"] = False
            return result
        
        for i, seq in enumerate(sequences):
            if isinstance(seq, dict):
                seq = seq.get('sequence', '')
            
            # Check sequence length
            if len(seq) > 1000000:  # 1MB sequence limit
                result["warnings"].append(f"Sequence {i+1} is very large ({len(seq)} characters)")
            
            # Check for suspicious patterns
            if self._contains_sensitive_data(seq):
                result["security_flags"].append(f"Sequence {i+1} may contain sensitive information")
            
            # Validate sequence characters
            valid_chars = set('ATCGRYKMSWBDHVNUIEFPQXZJ*-.')  # Extended for all sequence types
            invalid_chars = set(seq.upper()) - valid_chars
            
            if invalid_chars:
                result["warnings"].append(f"Sequence {i+1} contains unusual characters: {invalid_chars}")
        
        return result
    
    def _validate_file_upload(self, file_data: Dict) -> Dict:
        """Validate file upload for security"""
        
        result = {"valid": True, "errors": [], "warnings": [], "security_flags": []}
        
        filename = file_data.get('filename', '')
        file_size = file_data.get('size', 0)
        content_type = file_data.get('content_type', '')
        
        # Check file extension
        if '.' in filename:
            extension = filename.split('.')[-1].lower()
            if extension not in self.security_policy.allowed_file_types:
                result["errors"].append(f"File type '{extension}' not allowed")
                result["valid"] = False
        
        # Check file size
        max_size_bytes = self.security_policy.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            result["errors"].append(f"File size ({file_size} bytes) exceeds limit ({max_size_bytes} bytes)")
            result["valid"] = False
        
        # Check filename for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            result["security_flags"].append("Filename contains potentially dangerous characters")
            result["valid"] = False
        
        # Check for executable file indicators
        executable_extensions = ['.exe', '.bat', '.sh', '.cmd', '.scr']
        if any(filename.lower().endswith(ext) for ext in executable_extensions):
            result["security_flags"].append("File appears to be executable")
            result["valid"] = False
        
        return result
    
    def _validate_user_input(self, user_input: Any) -> Dict:
        """Validate user input for injection attacks"""
        
        result = {"valid": True, "errors": [], "warnings": [], "security_flags": []}
        
        if isinstance(user_input, str):
            inputs = [user_input]
        elif isinstance(user_input, list):
            inputs = [str(item) for item in user_input]
        elif isinstance(user_input, dict):
            inputs = [str(value) for value in user_input.values()]
        else:
            inputs = [str(user_input)]
        
        # Check for injection patterns
        injection_patterns = [
            r'<script.*?>',           # XSS
            r'javascript:',           # XSS
            r'on\w+\s*=',            # Event handlers
            r'union\s+select',        # SQL injection
            r'drop\s+table',          # SQL injection
            r'exec\s*\(',            # Code execution
            r'eval\s*\(',            # Code execution
            r'system\s*\(',          # System calls
            r'os\.',                 # OS module access
            r'subprocess\.',         # Subprocess access
            r'__import__',           # Import statements
        ]
        
        for i, input_str in enumerate(inputs):
            input_lower = input_str.lower()
            
            for pattern in injection_patterns:
                if re.search(pattern, input_lower, re.IGNORECASE):
                    result["security_flags"].append(f"Input {i+1} contains suspicious pattern: {pattern}")
                    result["valid"] = False
            
            # Check for excessively long input
            if len(input_str) > 10000:
                result["warnings"].append(f"Input {i+1} is very long ({len(input_str)} characters)")
            
            # Check for sensitive data patterns
            if self._contains_sensitive_data(input_str):
                result["security_flags"].append(f"Input {i+1} may contain sensitive information")
        
        return result
    
    def _contains_sensitive_data(self, text: str) -> bool:
        """Check if text contains sensitive data patterns"""
        
        text_lower = text.lower()
        
        for pattern in self.sensitive_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Check for API keys, tokens, etc.
        if re.search(r'[a-zA-Z0-9]{32,}', text):  # Long alphanumeric strings
            return True
        
        return False
    
    def sanitize_biological_data(self, data: Any) -> Any:
        """Sanitize biological data while preserving scientific integrity"""
        
        if isinstance(data, str):
            return self._sanitize_sequence_string(data)
        elif isinstance(data, list):
            return [self.sanitize_biological_data(item) for item in data]
        elif isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                sanitized_key = self._sanitize_string(key)
                sanitized_value = self.sanitize_biological_data(value)
                sanitized[sanitized_key] = sanitized_value
            return sanitized
        else:
            return data
    
    def _sanitize_sequence_string(self, sequence: str) -> str:
        """Sanitize sequence string while preserving biological validity"""
        
        # Remove HTML tags
        sequence = re.sub(r'<[^>]+>', '', sequence)
        
        # Remove script content
        sequence = re.sub(r'<script.*?</script>', '', sequence, flags=re.IGNORECASE | re.DOTALL)
        
        # Keep only valid biological characters
        valid_chars = set('ATCGRYKMSWBDHVNUatcgrykmswbdhvnu*-.')
        sanitized = ''.join(char for char in sequence if char in valid_chars)
        
        return sanitized
    
    def _sanitize_string(self, text: str) -> str:
        """General string sanitization"""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove script content
        text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove potential injection attempts
        text = re.sub(r'[<>"\']', '', text)
        
        return text.strip()
    
    def check_rate_limit(self, user_id: str, ip_address: str) -> Dict:
        """Check rate limiting for user"""
        
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(minutes=1)
        
        # Clean old entries
        self._cleanup_rate_limit_storage(window_start)
        
        # Check user rate limit
        user_key = f"user_{user_id}"
        ip_key = f"ip_{ip_address}"
        
        user_requests = self.rate_limit_storage.get(user_key, [])
        ip_requests = self.rate_limit_storage.get(ip_key, [])
        
        # Count recent requests
        recent_user_requests = [req for req in user_requests if req > window_start]
        recent_ip_requests = [req for req in ip_requests if req > window_start]
        
        # Check limits
        max_requests = self.security_policy.rate_limit_requests_per_minute
        
        if len(recent_user_requests) >= max_requests:
            self._audit_log('rate_limit_exceeded', user_id, {'type': 'user', 'requests': len(recent_user_requests)})
            return {
                "allowed": False,
                "reason": "User rate limit exceeded",
                "requests_in_window": len(recent_user_requests),
                "window_reset_time": (window_start + timedelta(minutes=1)).isoformat()
            }
        
        if len(recent_ip_requests) >= max_requests * 2:  # Higher limit for IP
            self._audit_log('rate_limit_exceeded', user_id, {'type': 'ip', 'requests': len(recent_ip_requests)})
            return {
                "allowed": False,
                "reason": "IP rate limit exceeded",
                "requests_in_window": len(recent_ip_requests),
                "window_reset_time": (window_start + timedelta(minutes=1)).isoformat()
            }
        
        # Record this request
        recent_user_requests.append(current_time)
        recent_ip_requests.append(current_time)
        
        self.rate_limit_storage[user_key] = recent_user_requests
        self.rate_limit_storage[ip_key] = recent_ip_requests
        
        return {
            "allowed": True,
            "requests_remaining": max_requests - len(recent_user_requests),
            "window_reset_time": (window_start + timedelta(minutes=1)).isoformat()
        }
    
    def _cleanup_rate_limit_storage(self, cutoff_time: datetime):
        """Clean up old rate limit entries"""
        
        for key in list(self.rate_limit_storage.keys()):
            self.rate_limit_storage[key] = [
                req_time for req_time in self.rate_limit_storage[key] 
                if req_time > cutoff_time
            ]
            
            # Remove empty entries
            if not self.rate_limit_storage[key]:
                del self.rate_limit_storage[key]
    
    def encrypt_sensitive_data(self, data: str, context: str = "general") -> str:
        """Encrypt sensitive data"""
        
        try:
            from cryptography.fernet import Fernet
            
            # Generate key from secret (in production, use proper key management)
            key_material = hashlib.sha256(f"{self.secret_key}_{context}".encode()).digest()
            key = base64.urlsafe_b64encode(key_material[:32])
            
            fernet = Fernet(key)
            encrypted = fernet.encrypt(data.encode('utf-8'))
            
            return encrypted.decode('utf-8')
            
        except ImportError:
            logger.warning("Cryptography library not available, using base64 encoding")
            import base64
            return base64.b64encode(data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            raise SecurityException("Encryption failed")
    
    def decrypt_sensitive_data(self, encrypted_data: str, context: str = "general") -> str:
        """Decrypt sensitive data"""
        
        try:
            from cryptography.fernet import Fernet
            
            # Generate same key
            key_material = hashlib.sha256(f"{self.secret_key}_{context}".encode()).digest()
            key = base64.urlsafe_b64encode(key_material[:32])
            
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted_data.encode('utf-8'))
            
            return decrypted.decode('utf-8')
            
        except ImportError:
            logger.warning("Cryptography library not available, using base64 decoding")
            import base64
            return base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            raise SecurityException("Decryption failed")
    
    def generate_secure_filename(self, original_filename: str, user_id: str) -> str:
        """Generate secure filename for uploaded files"""
        
        # Extract extension
        extension = ''
        if '.' in original_filename:
            extension = '.' + original_filename.split('.')[-1].lower()
        
        # Generate secure name
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        random_suffix = secrets.token_hex(8)
        secure_name = f"{user_id}_{timestamp}_{random_suffix}{extension}"
        
        return secure_name
    
    def check_permissions(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        
        # Admin users have all permissions
        if 'admin' in user_permissions:
            return True
        
        # Check specific permission
        return required_permission in user_permissions
    
    def _audit_log(self, action: str, user_id: str, details: Dict = None):
        """Add entry to audit log"""
        
        if details is None:
            details = {}
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'user_id': user_id,
            'details': details,
            'log_id': str(uuid.uuid4())
        }
        
        self.audit_log.append(log_entry)
        
        # Cleanup old logs
        cutoff_time = datetime.utcnow() - timedelta(days=self.security_policy.audit_log_retention_days)
        self.audit_log = [
            entry for entry in self.audit_log 
            if datetime.fromisoformat(entry['timestamp']) > cutoff_time
        ]
        
        logger.info(f"Audit log: {action} by user {user_id}")
    
    def get_audit_logs(self, user_id: str = None, action: str = None, limit: int = 100) -> List[Dict]:
        """Get audit logs with optional filtering"""
        
        filtered_logs = self.audit_log
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log['user_id'] == user_id]
        
        if action:
            filtered_logs = [log for log in filtered_logs if log['action'] == action]
        
        # Sort by timestamp (newest first) and limit
        filtered_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return filtered_logs[:limit]
    
    def _invalidate_session(self, user_id: str):
        """Invalidate user session"""
        
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            self._audit_log('session_invalidated', user_id)
    
    def invalidate_all_sessions(self, user_id: str):
        """Invalidate all sessions for a user"""
        
        self._invalidate_session(user_id)
        self._audit_log('all_sessions_invalidated', user_id)
    
    def get_security_report(self) -> Dict:
        """Generate security status report"""
        
        current_time = datetime.utcnow()
        
        # Active sessions analysis
        active_session_count = len(self.active_sessions)
        expired_sessions = 0
        
        for user_id, session in list(self.active_sessions.items()):
            session_age = (current_time - session.created_at).total_seconds()
            if session_age > (self.security_policy.session_timeout_hours * 3600):
                expired_sessions += 1
                self._invalidate_session(user_id)
        
        # Recent security events
        recent_cutoff = current_time - timedelta(hours=24)
        recent_security_events = [
            log for log in self.audit_log
            if datetime.fromisoformat(log['timestamp']) > recent_cutoff
            and log['action'] in ['rate_limit_exceeded', 'invalid_token', 'unauthorized_access']
        ]
        
        return {
            "generated_at": current_time.isoformat(),
            "active_sessions": active_session_count,
            "expired_sessions_cleaned": expired_sessions,
            "security_policy": {
                "max_file_size_mb": self.security_policy.max_file_size_mb,
                "session_timeout_hours": self.security_policy.session_timeout_hours,
                "rate_limit_per_minute": self.security_policy.rate_limit_requests_per_minute,
                "allowed_file_types": self.security_policy.allowed_file_types
            },
            "recent_security_events": len(recent_security_events),
            "audit_log_entries": len(self.audit_log),
            "rate_limit_tracking": len(self.rate_limit_storage)
        }
    
    def update_security_policy(self, policy_updates: Dict) -> Dict:
        """Update security policy settings"""
        
        try:
            # Validate policy updates
            valid_settings = {
                'max_file_size_mb', 'allowed_file_types', 'max_sequences_per_request',
                'rate_limit_requests_per_minute', 'session_timeout_hours', 'require_2fa'
            }
            
            invalid_settings = set(policy_updates.keys()) - valid_settings
            if invalid_settings:
                return {"error": f"Invalid policy settings: {invalid_settings}"}
            
            # Apply updates
            for setting, value in policy_updates.items():
                if hasattr(self.security_policy, setting):
                    setattr(self.security_policy, setting, value)
            
            self._audit_log('security_policy_updated', 'system', policy_updates)
            
            return {
                "status": "success",
                "updated_settings": list(policy_updates.keys()),
                "message": "Security policy updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating security policy: {str(e)}")
            return {"error": f"Policy update failed: {str(e)}"}

class SecurityException(Exception):
    """Custom exception for security-related errors"""
    pass

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # In a real implementation, this would extract user info from request
            # For now, assume user permissions are passed in kwargs
            user_permissions = kwargs.get('user_permissions', [])
            
            if not biological_security.check_permissions(user_permissions, permission):
                raise SecurityException(f"Insufficient permissions: {permission} required")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def audit_log_action(action: str):
    """Decorator to automatically log actions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id', 'unknown')
            
            try:
                result = await func(*args, **kwargs)
                biological_security._audit_log(action, user_id, {'success': True})
                return result
            except Exception as e:
                biological_security._audit_log(action, user_id, {'success': False, 'error': str(e)})
                raise
        return wrapper
    return decorator

# Global security instance
biological_security = BiologicalDataSecurity()

# Import base64 for fallback encryption
import base64