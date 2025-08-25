# backend/app/services/cache_manager.py
import asyncio
import redis
import pickle
import hashlib
import json
import gzip
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass
from functools import wraps
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry metadata"""
    key: str
    size_bytes: int
    created_at: datetime
    expires_at: Optional[datetime]
    hit_count: int
    last_accessed: datetime
    data_type: str
    compression_used: bool

@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_entries: int
    total_size_mb: float
    hit_rate: float
    miss_rate: float
    eviction_count: int
    memory_usage_percent: float
    avg_response_time_ms: float

class BioinformaticsCacheManager:
    """Multi-level caching system optimized for biological data"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        # Initialize Redis client
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            self.redis_available = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory cache: {e}")
            self.redis_available = False
            self.redis_client = None
        
        # In-memory cache fallback
        self.memory_cache = {}
        self.cache_metadata = {}
        
        # Cache configuration
        self.cache_config = {
            'default_ttl': 3600,  # 1 hour
            'max_memory_mb': 1024,  # 1GB
            'compression_threshold': 1024,  # 1KB
            'enable_compression': True,
            'max_key_length': 250,
            'cache_prefixes': {
                'sequence': 'seq:',
                'analysis': 'analysis:',
                'alignment': 'align:',
                'blast': 'blast:',
                'annotation': 'anno:',
                'workflow': 'wf:',
                'user': 'user:',
                'file': 'file:'
            }
        }
        
        # Performance tracking
        self.performance_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'total_requests': 0,
            'total_response_time': 0.0
        }
    
    def cached_analysis(self, namespace: str, ttl: int = 3600, compression: bool = None):
        """Decorator for caching analysis results"""
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self._generate_cache_key(namespace, func.__name__, args, kwargs)
                
                # Try to get from cache
                start_time = asyncio.get_event_loop().time()
                cached_result = await self.get(cache_key)
                
                if cached_result is not None:
                    self.performance_stats['hits'] += 1
                    self.performance_stats['total_requests'] += 1
                    
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    self.performance_stats['total_response_time'] += response_time
                    
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_result
                
                # Cache miss - execute function
                self.performance_stats['misses'] += 1
                self.performance_stats['total_requests'] += 1
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Cache the result
                    use_compression = compression if compression is not None else self.cache_config['enable_compression']
                    await self.set(cache_key, result, ttl, compression=use_compression)
                    
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    self.performance_stats['total_response_time'] += response_time
                    
                    logger.debug(f"Cache miss for {cache_key}, result cached")
                    return result
                    
                except Exception as e:
                    logger.error(f"Error in cached function {func.__name__}: {str(e)}")
                    raise
            
            return wrapper
        return decorator
    
    async def get(self, key: str, namespace: str = None) -> Optional[Any]:
        """Get value from cache"""
        
        full_key = self._build_full_key(key, namespace)
        
        try:
            if self.redis_available:
                data = self.redis_client.get(full_key)
                if data is not None:
                    # Update access statistics
                    await self._update_access_stats(full_key)
                    return self._deserialize_data(data)
            else:
                # Use in-memory cache
                if full_key in self.memory_cache:
                    entry = self.memory_cache[full_key]
                    
                    # Check expiration
                    if entry['expires_at'] and datetime.utcnow() > entry['expires_at']:
                        del self.memory_cache[full_key]
                        if full_key in self.cache_metadata:
                            del self.cache_metadata[full_key]
                        return None
                    
                    # Update access statistics
                    await self._update_access_stats(full_key)
                    return entry['data']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache key {full_key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None, namespace: str = None, compression: bool = None) -> bool:
        """Set value in cache"""
        
        full_key = self._build_full_key(key, namespace)
        
        if ttl is None:
            ttl = self.cache_config['default_ttl']
        
        try:
            # Serialize and optionally compress data
            serialized_data = self._serialize_data(value, compression)
            
            if self.redis_available:
                # Use Redis
                success = self.redis_client.setex(full_key, ttl, serialized_data)
                
                if success:
                    # Store metadata
                    await self._store_cache_metadata(full_key, value, ttl, compression or False)
                    self.performance_stats['sets'] += 1
                
                return bool(success)
            else:
                # Use in-memory cache
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                
                self.memory_cache[full_key] = {
                    'data': value,
                    'expires_at': expires_at,
                    'created_at': datetime.utcnow()
                }
                
                await self._store_cache_metadata(full_key, value, ttl, compression or False)
                self.performance_stats['sets'] += 1
                
                # Check memory usage
                await self._cleanup_memory_cache()
                
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache key {full_key}: {str(e)}")
            return False
    
    async def delete(self, key: str, namespace: str = None) -> bool:
        """Delete value from cache"""
        
        full_key = self._build_full_key(key, namespace)
        
        try:
            if self.redis_available:
                result = self.redis_client.delete(full_key)
                deleted = result > 0
            else:
                deleted = full_key in self.memory_cache
                if deleted:
                    del self.memory_cache[full_key]
            
            if deleted:
                if full_key in self.cache_metadata:
                    del self.cache_metadata[full_key]
                self.performance_stats['deletes'] += 1
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting cache key {full_key}: {str(e)}")
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all entries in a namespace"""
        
        prefix = self.cache_config['cache_prefixes'].get(namespace, f"{namespace}:")
        
        try:
            if self.redis_available:
                # Get all keys with prefix
                keys = self.redis_client.keys(f"{prefix}*")
                if keys:
                    deleted = self.redis_client.delete(*keys)
                else:
                    deleted = 0
            else:
                # Clear from memory cache
                keys_to_delete = [key for key in self.memory_cache.keys() if key.startswith(prefix)]
                deleted = len(keys_to_delete)
                
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    if key in self.cache_metadata:
                        del self.cache_metadata[key]
            
            logger.info(f"Cleared {deleted} entries from namespace {namespace}")
            return deleted
            
        except Exception as e:
            logger.error(f"Error clearing namespace {namespace}: {str(e)}")
            return 0
    
    async def cache_sequence_analysis(self, sequences: List[Dict], analysis_type: str, result: Any, ttl: int = 7200):
        """Cache sequence analysis results with optimized key generation"""
        
        # Generate key based on sequence content and analysis type
        sequence_hash = self._hash_sequences(sequences)
        cache_key = f"seq_analysis:{analysis_type}:{sequence_hash}"
        
        return await self.set(cache_key, result, ttl, compression=True)
    
    async def get_cached_sequence_analysis(self, sequences: List[Dict], analysis_type: str) -> Optional[Any]:
        """Get cached sequence analysis results"""
        
        sequence_hash = self._hash_sequences(sequences)
        cache_key = f"seq_analysis:{analysis_type}:{sequence_hash}"
        
        return await self.get(cache_key)
    
    async def cache_blast_results(self, query_sequence: str, database: str, parameters: Dict, result: Any):
        """Cache BLAST search results"""
        
        # Generate deterministic key for BLAST search
        query_hash = hashlib.md5(query_sequence.encode()).hexdigest()
        param_hash = hashlib.md5(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        cache_key = f"blast:{database}:{query_hash}:{param_hash}"
        
        # BLAST results are valuable, cache for longer
        return await self.set(cache_key, result, ttl=86400, compression=True)  # 24 hours
    
    async def get_cached_blast_results(self, query_sequence: str, database: str, parameters: Dict) -> Optional[Any]:
        """Get cached BLAST results"""
        
        query_hash = hashlib.md5(query_sequence.encode()).hexdigest()
        param_hash = hashlib.md5(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        cache_key = f"blast:{database}:{query_hash}:{param_hash}"
        
        return await self.get(cache_key)
    
    def _generate_cache_key(self, namespace: str, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function arguments"""
        
        # Create deterministic representation of arguments
        key_data = {
            'function': func_name,
            'args': str(args),
            'kwargs': {k: str(v) for k, v in kwargs.items()}
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        prefix = self.cache_config['cache_prefixes'].get(namespace, f"{namespace}:")
        return f"{prefix}{func_name}:{key_hash}"
    
    def _hash_sequences(self, sequences: List[Dict]) -> str:
        """Generate hash for sequence list"""
        
        # Create deterministic hash of sequences
        sequence_strings = []
        for seq in sequences:
            seq_str = seq.get('sequence', '')
            seq_id = seq.get('id', seq.get('name', ''))
            sequence_strings.append(f"{seq_id}:{seq_str}")
        
        combined = '|'.join(sorted(sequence_strings))
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _build_full_key(self, key: str, namespace: str = None) -> str:
        """Build full cache key with namespace"""
        
        if namespace:
            prefix = self.cache_config['cache_prefixes'].get(namespace, f"{namespace}:")
            full_key = f"{prefix}{key}"
        else:
            full_key = key
        
        # Ensure key length is within limits
        if len(full_key) > self.cache_config['max_key_length']:
            # Hash long keys
            key_hash = hashlib.sha256(full_key.encode()).hexdigest()[:32]
            full_key = f"hashed:{key_hash}"
        
        return full_key
    
    def _serialize_data(self, data: Any, use_compression: bool = None) -> bytes:
        """Serialize data for caching"""
        
        if use_compression is None:
            use_compression = self.cache_config['enable_compression']
        
        # Handle different data types efficiently
        if isinstance(data, pd.DataFrame):
            # Efficient DataFrame serialization
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        elif isinstance(data, np.ndarray):
            # Efficient NumPy array serialization
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        elif isinstance(data, (dict, list)):
            # JSON serialization for simple structures
            try:
                serialized = json.dumps(data, default=str).encode('utf-8')
            except (TypeError, ValueError):
                # Fallback to pickle for complex objects
                serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # General pickle serialization
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Compress if enabled and data is large enough
        if use_compression and len(serialized) > self.cache_config['compression_threshold']:
            serialized = gzip.compress(serialized)
        
        return serialized
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize cached data"""
        
        try:
            # Check if data is compressed
            if data.startswith(b'\x1f\x8b'):  # gzip magic number
                data = gzip.decompress(data)
            
            # Try JSON first (faster)
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fallback to pickle
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"Error deserializing cached data: {str(e)}")
            return None
    
    async def _store_cache_metadata(self, key: str, value: Any, ttl: int, compression: bool):
        """Store metadata about cached entry"""
        
        try:
            serialized_size = len(self._serialize_data(value, compression))
            
            metadata = CacheEntry(
                key=key,
                size_bytes=serialized_size,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None,
                hit_count=0,
                last_accessed=datetime.utcnow(),
                data_type=type(value).__name__,
                compression_used=compression
            )
            
            self.cache_metadata[key] = metadata
            
        except Exception as e:
            logger.error(f"Error storing cache metadata: {str(e)}")
    
    async def _update_access_stats(self, key: str):
        """Update access statistics for cache entry"""
        
        if key in self.cache_metadata:
            metadata = self.cache_metadata[key]
            metadata.hit_count += 1
            metadata.last_accessed = datetime.utcnow()
    
    async def _cleanup_memory_cache(self):
        """Clean up memory cache if it exceeds limits"""
        
        if not self.memory_cache:
            return
        
        # Calculate current memory usage
        total_size = sum(
            len(self._serialize_data(entry['data'])) 
            for entry in self.memory_cache.values()
        )
        
        max_size = self.cache_config['max_memory_mb'] * 1024 * 1024
        
        if total_size > max_size:
            # Remove expired entries first
            await self._remove_expired_entries()
            
            # If still over limit, remove least recently used
            if len(self.memory_cache) > 0:
                await self._evict_lru_entries(max_size * 0.8)  # Evict to 80% of limit
    
    async def _remove_expired_entries(self):
        """Remove expired entries from memory cache"""
        
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, entry in self.memory_cache.items():
            if entry.get('expires_at') and current_time > entry['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            if key in self.cache_metadata:
                del self.cache_metadata[key]
            self.performance_stats['evictions'] += 1
    
    async def _evict_lru_entries(self, target_size: float):
        """Evict least recently used entries"""
        
        # Sort by last accessed time
        sorted_metadata = sorted(
            self.cache_metadata.items(),
            key=lambda x: x[1].last_accessed
        )
        
        current_size = sum(
            len(self._serialize_data(entry['data'])) 
            for entry in self.memory_cache.values()
        )
        
        for key, metadata in sorted_metadata:
            if current_size <= target_size:
                break
            
            if key in self.memory_cache:
                entry_size = len(self._serialize_data(self.memory_cache[key]['data']))
                del self.memory_cache[key]
                del self.cache_metadata[key]
                current_size -= entry_size
                self.performance_stats['evictions'] += 1
    
    async def get_cache_stats(self) -> CacheStats:
        """Get comprehensive cache statistics"""
        
        try:
            total_entries = len(self.cache_metadata)
            total_size_bytes = sum(metadata.size_bytes for metadata in self.cache_metadata.values())
            total_size_mb = total_size_bytes / (1024 * 1024)
            
            total_requests = self.performance_stats['hits'] + self.performance_stats['misses']
            hit_rate = (self.performance_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            miss_rate = 100 - hit_rate
            
            avg_response_time = (
                self.performance_stats['total_response_time'] / total_requests
                if total_requests > 0 else 0
            )
            
            # Memory usage calculation
            max_memory = self.cache_config['max_memory_mb'] * 1024 * 1024
            memory_usage_percent = (total_size_bytes / max_memory * 100) if max_memory > 0 else 0
            
            return CacheStats(
                total_entries=total_entries,
                total_size_mb=total_size_mb,
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                eviction_count=self.performance_stats['evictions'],
                memory_usage_percent=memory_usage_percent,
                avg_response_time_ms=avg_response_time
            )
            
        except Exception as e:
            logger.error(f"Error calculating cache stats: {str(e)}")
            return CacheStats(0, 0.0, 0.0, 0.0, 0, 0.0, 0.0)
    
    async def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health status"""
        
        health = {
            "status": "healthy",
            "redis_available": self.redis_available,
            "issues": [],
            "recommendations": []
        }
        
        try:
            stats = await self.get_cache_stats()
            
            # Check hit rate
            if stats.hit_rate < 50:
                health["issues"].append("Low cache hit rate")
                health["recommendations"].append("Consider increasing TTL values")
                health["status"] = "degraded"
            
            # Check memory usage
            if stats.memory_usage_percent > 90:
                health["issues"].append("High memory usage")
                health["recommendations"].append("Consider increasing cache size limit or cleaning old entries")
                health["status"] = "degraded"
            
            # Check eviction rate
            if stats.eviction_count > 1000:
                health["issues"].append("High eviction rate")
                health["recommendations"].append("Consider increasing cache size or optimizing key selection")
                if health["status"] != "degraded":
                    health["status"] = "degraded"
            
            # Redis connection health
            if self.redis_available:
                try:
                    self.redis_client.ping()
                except:
                    health["issues"].append("Redis connection issues")
                    health["status"] = "degraded"
            
            health["stats"] = stats
            
            return health
            
        except Exception as e:
            logger.error(f"Error checking cache health: {str(e)}")
            health["status"] = "down"
            health["issues"].append(f"Health check failed: {str(e)}")
            return health
    
    async def warm_cache(self, warm_up_data: List[Dict]) -> Dict:
        """Pre-populate cache with frequently accessed data"""
        
        warmed_count = 0
        failed_count = 0
        
        try:
            for data_item in warm_up_data:
                cache_key = data_item.get('key')
                cache_value = data_item.get('value')
                cache_ttl = data_item.get('ttl', self.cache_config['default_ttl'])
                namespace = data_item.get('namespace')
                
                if cache_key and cache_value is not None:
                    success = await self.set(cache_key, cache_value, cache_ttl, namespace)
                    if success:
                        warmed_count += 1
                    else:
                        failed_count += 1
            
            return {
                "status": "success",
                "warmed_entries": warmed_count,
                "failed_entries": failed_count,
                "total_attempted": len(warm_up_data)
            }
            
        except Exception as e:
            logger.error(f"Error warming cache: {str(e)}")
            return {"error": f"Cache warming failed: {str(e)}"}
    
    async def optimize_cache(self) -> Dict:
        """Optimize cache performance"""
        
        optimization_results = {
            "actions_taken": [],
            "space_freed_mb": 0,
            "entries_removed": 0
        }
        
        try:
            # Remove expired entries
            await self._remove_expired_entries()
            optimization_results["actions_taken"].append("Removed expired entries")
            
            # Analyze access patterns
            access_analysis = await self._analyze_access_patterns()
            
            # Remove rarely accessed entries
            if access_analysis["low_access_entries"] > 0:
                removed = await self._remove_low_access_entries()
                optimization_results["entries_removed"] += removed
                optimization_results["actions_taken"].append(f"Removed {removed} rarely accessed entries")
            
            # Compress large uncompressed entries
            compressed_count = await self._compress_large_entries()
            if compressed_count > 0:
                optimization_results["actions_taken"].append(f"Compressed {compressed_count} large entries")
            
            # Update configuration based on usage patterns
            config_updates = await self._optimize_configuration(access_analysis)
            if config_updates:
                optimization_results["actions_taken"].append("Updated cache configuration")
            
            return {
                "status": "success",
                "optimization_results": optimization_results
            }
            
        except Exception as e:
            logger.error(f"Error optimizing cache: {str(e)}")
            return {"error": f"Cache optimization failed: {str(e)}"}
    
    async def _analyze_access_patterns(self) -> Dict:
        """Analyze cache access patterns"""
        
        if not self.cache_metadata:
            return {"low_access_entries": 0, "high_access_entries": 0}
        
        # Calculate access frequency statistics
        hit_counts = [metadata.hit_count for metadata in self.cache_metadata.values()]
        
        if not hit_counts:
            return {"low_access_entries": 0, "high_access_entries": 0}
        
        mean_hits = np.mean(hit_counts)
        std_hits = np.std(hit_counts)
        
        low_threshold = max(0, mean_hits - std_hits)
        high_threshold = mean_hits + std_hits
        
        low_access_entries = sum(1 for hits in hit_counts if hits < low_threshold)
        high_access_entries = sum(1 for hits in hit_counts if hits > high_threshold)
        
        return {
            "total_entries": len(hit_counts),
            "mean_hits": mean_hits,
            "low_access_entries": low_access_entries,
            "high_access_entries": high_access_entries,
            "access_distribution": {
                "min": min(hit_counts),
                "max": max(hit_counts),
                "median": np.median(hit_counts)
            }
        }
    
    async def _remove_low_access_entries(self) -> int:
        """Remove entries with very low access count"""
        
        removed_count = 0
        current_time = datetime.utcnow()
        
        # Find entries that haven't been accessed recently and have low hit count
        keys_to_remove = []
        
        for key, metadata in self.cache_metadata.items():
            age_hours = (current_time - metadata.created_at).total_seconds() / 3600
            
            # Remove if old and rarely accessed
            if age_hours > 24 and metadata.hit_count < 2:
                keys_to_remove.append(key)
            elif age_hours > 72 and metadata.hit_count < 5:
                keys_to_remove.append(key)
        
        # Remove identified entries
        for key in keys_to_remove:
            if await self.delete(key):
                removed_count += 1
        
        return removed_count
    
    async def _compress_large_entries(self) -> int:
        """Compress large uncompressed entries"""
        
        compressed_count = 0
        
        for key, metadata in self.cache_metadata.items():
            if (not metadata.compression_used and 
                metadata.size_bytes > self.cache_config['compression_threshold']):
                
                # Re-cache with compression
                try:
                    value = await self.get(key)
                    if value is not None:
                        # Determine TTL from expiration
                        ttl = 3600  # Default
                        if metadata.expires_at:
                            remaining = (metadata.expires_at - datetime.utcnow()).total_seconds()
                            ttl = max(60, int(remaining))
                        
                        await self.set(key, value, ttl, compression=True)
                        compressed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error compressing cache entry {key}: {str(e)}")
        
        return compressed_count
    
    async def _optimize_configuration(self, access_analysis: Dict) -> Dict:
        """Optimize cache configuration based on usage patterns"""
        
        updates = {}
        
        # Adjust TTL based on access patterns
        if access_analysis.get("high_access_entries", 0) > access_analysis.get("total_entries", 0) * 0.3:
            # Many high-access entries, increase default TTL
            new_ttl = min(self.cache_config['default_ttl'] * 1.5, 7200)
            if new_ttl != self.cache_config['default_ttl']:
                self.cache_config['default_ttl'] = int(new_ttl)
                updates['default_ttl'] = new_ttl
        
        # Adjust compression threshold
        avg_size = np.mean([metadata.size_bytes for metadata in self.cache_metadata.values()])
        if avg_size > self.cache_config['compression_threshold'] * 2:
            new_threshold = int(avg_size * 0.5)
            self.cache_config['compression_threshold'] = new_threshold
            updates['compression_threshold'] = new_threshold
        
        return updates
    
    async def bulk_cache_sequences(self, sequences: List[Dict], analysis_results: Dict) -> Dict:
        """Efficiently cache multiple sequence analysis results"""
        
        cached_count = 0
        failed_count = 0
        
        try:
            for analysis_type, results in analysis_results.items():
                success = await self.cache_sequence_analysis(sequences, analysis_type, results)
                if success:
                    cached_count += 1
                else:
                    failed_count += 1
            
            return {
                "status": "success",
                "cached_analyses": cached_count,
                "failed_caches": failed_count
            }
            
        except Exception as e:
            logger.error(f"Error in bulk caching: {str(e)}")
            return {"error": f"Bulk caching failed: {str(e)}"}
    
    async def invalidate_related_cache(self, entity_type: str, entity_id: str):
        """Invalidate cache entries related to a specific entity"""
        
        invalidated_count = 0
        
        try:
            # Find keys related to the entity
            related_keys = []
            
            for key in self.cache_metadata.keys():
                if entity_id in key or f"{entity_type}:{entity_id}" in key:
                    related_keys.append(key)
            
            # Delete related entries
            for key in related_keys:
                if await self.delete(key):
                    invalidated_count += 1
            
            logger.info(f"Invalidated {invalidated_count} cache entries for {entity_type}:{entity_id}")
            
            return {
                "status": "success",
                "invalidated_count": invalidated_count,
                "entity_type": entity_type,
                "entity_id": entity_id
            }
            
        except Exception as e:
            logger.error(f"Error invalidating related cache: {str(e)}")
            return {"error": f"Cache invalidation failed: {str(e)}"}

# Performance monitoring decorator
def monitor_performance(operation_name: str):
    """Decorator to monitor performance of cached operations"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = asyncio.get_event_loop().time()
            
            try:
                result = await func(*args, **kwargs)
                
                end_time = asyncio.get_event_loop().time()
                execution_time = end_time - start_time
                
                # Log performance metrics
                logger.info(f"Operation {operation_name} completed in {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                end_time = asyncio.get_event_loop().time()
                execution_time = end_time - start_time
                
                logger.error(f"Operation {operation_name} failed after {execution_time:.3f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator

# Global cache manager instance
bioinformatics_cache = BioinformaticsCacheManager()