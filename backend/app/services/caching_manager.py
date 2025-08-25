# backend/app/services/caching_manager.py
import redis
import pickle
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class BioinformaticsCacheManager:
    """Multi-level caching for biological data and analysis results"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_client = redis.Redis.from_url(redis_url)
        self.local_cache = {}  # In-memory cache for frequently accessed data
        self.cache_stats = {"hits": 0, "misses": 0}
        
        # Cache configuration
        self.cache_config = {
            "sequence_analysis": {"ttl": 3600, "namespace": "seq_analysis"},
            "blast_search": {"ttl": 86400, "namespace": "blast"},  # 24 hours
            "alignment": {"ttl": 7200, "namespace": "alignment"},  # 2 hours
            "phylogeny": {"ttl": 86400, "namespace": "phylo"},
            "structure_prediction": {"ttl": 604800, "namespace": "structure"},  # 1 week
            "gene_prediction": {"ttl": 43200, "namespace": "genes"},  # 12 hours
            "domain_search": {"ttl": 86400, "namespace": "domains"},
            "sequence_stats": {"ttl": 1800, "namespace": "stats"}  # 30 minutes
        }
    
    def cached_analysis(self, analysis_type: str, ttl: Optional[int] = None):
        """Decorator for caching analysis results"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(analysis_type, args, kwargs)
                
                # Try cache first
                cached_result = await self._get_from_cache(cache_key, analysis_type)
                if cached_result is not None:
                    self.cache_stats["hits"] += 1
                    logger.info(f"Cache hit for {analysis_type}: {cache_key}")
                    return cached_result
                
                self.cache_stats["misses"] += 1
                logger.info(f"Cache miss for {analysis_type}: {cache_key}")
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self._set_to_cache(cache_key, result, analysis_type, ttl)
                
                return result
            return wrapper
        return decorator
    
    async def _get_from_cache(self, cache_key: str, analysis_type: str) -> Optional[Any]:
        """Get data from cache (local first, then Redis)"""
        try:
            # Check local cache first
            if cache_key in self.local_cache:
                cached_item = self.local_cache[cache_key]
                if datetime.now() < cached_item["expires_at"]:
                    return cached_item["data"]
                else:
                    del self.local_cache[cache_key]
            
            # Check Redis cache
            redis_key = f"{self.cache_config[analysis_type]['namespace']}:{cache_key}"
            cached_data = self.redis_client.get(redis_key)
            
            if cached_data:
                result = pickle.loads(cached_data)
                
                # Store in local cache for faster access
                local_ttl = min(300, self.cache_config[analysis_type]["ttl"] // 10)  # 5 minutes or 10% of Redis TTL
                self.local_cache[cache_key] = {
                    "data": result,
                    "expires_at": datetime.now() + timedelta(seconds=local_ttl)
                }
                
                return result
        
        except Exception as e:
            logger.warning(f"Cache get error for {cache_key}: {str(e)}")
        
        return None
    
    async def _set_to_cache(self, cache_key: str, data: Any, analysis_type: str, ttl: Optional[int] = None):
        """Set data in cache"""
        try:
            config = self.cache_config.get(analysis_type, {"ttl": 3600, "namespace": "default"})
            cache_ttl = ttl or config["ttl"]
            
            # Store in Redis
            redis_key = f"{config['namespace']}:{cache_key}"
            serialized_data = pickle.dumps(data)
            self.redis_client.setex(redis_key, cache_ttl, serialized_data)
            
            # Store in local cache
            local_ttl = min(300, cache_ttl // 10)
            self.local_cache[cache_key] = {
                "data": data,
                "expires_at": datetime.now() + timedelta(seconds=local_ttl)
            }
            
            logger.info(f"Cached {analysis_type} result: {cache_key} (TTL: {cache_ttl}s)")
        
        except Exception as e:
            logger.error(f"Cache set error for {cache_key}: {str(e)}")
    
    def _generate_cache_key(self, analysis_type: str, args: tuple, kwargs: dict) -> str:
        """Generate a unique cache key for the analysis"""
        key_data = {
            "type": analysis_type,
            "args": args,
            "kwargs": kwargs
        }
        
        # Convert to stable string representation
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def cache_sequence_data(self, sequence_id: str, sequence_data: Dict, ttl: int = 3600):
        """Cache sequence data with metadata"""
        cache_key = f"sequence:{sequence_id}"
        
        # Add caching metadata
        cached_data = {
            "data": sequence_data,
            "cached_at": datetime.now().isoformat(),
            "sequence_hash": hashlib.md5(sequence_data.get("sequence", "").encode()).hexdigest()
        }
        
        await self._set_to_cache(cache_key, cached_data, "sequence_stats", ttl)
    
    async def get_cached_sequence_data(self, sequence_id: str) -> Optional[Dict]:
        """Get cached sequence data"""
        cache_key = f"sequence:{sequence_id}"
        cached_data = await self._get_from_cache(cache_key, "sequence_stats")
        
        if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
            return cached_data["data"]
        
        return cached_data
    
    async def cache_batch_results(self, analysis_type: str, results: List[Dict], 
                                common_params: Dict, ttl: Optional[int] = None):
        """Cache batch analysis results"""
        for i, result in enumerate(results):
            batch_key = self._generate_cache_key(f"{analysis_type}_batch_{i}", (), common_params)
            await self._set_to_cache(batch_key, result, analysis_type, ttl)
    
    async def invalidate_cache(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        try:
            # Clear local cache
            keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.local_cache[key]
            
            # Clear Redis cache
            for namespace in [config["namespace"] for config in self.cache_config.values()]:
                redis_pattern = f"{namespace}:*{pattern}*"
                keys = self.redis_client.keys(redis_pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries matching {redis_pattern}")
        
        except Exception as e:
            logger.error(f"Cache invalidation error: {str(e)}")
    
    async def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        try:
            redis_info = self.redis_client.info()
            
            # Calculate hit rate
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hit_rate": round(hit_rate, 2),
                "total_hits": self.cache_stats["hits"],
                "total_misses": self.cache_stats["misses"],
                "local_cache_size": len(self.local_cache),
                "redis_used_memory": redis_info.get("used_memory_human", "N/A"),
                "redis_connected_clients": redis_info.get("connected_clients", 0),
                "cache_namespaces": list(set(config["namespace"] for config in self.cache_config.values()))
            }
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"error": str(e)}
    
    async def warm_cache(self, sequence_ids: List[str], analysis_types: List[str]):
        """Pre-warm cache for frequently accessed data"""
        logger.info(f"Warming cache for {len(sequence_ids)} sequences and {len(analysis_types)} analysis types")
        
        # This would typically involve running common analyses on popular sequences
        # Implementation depends on your specific use case
        
        tasks = []
        for seq_id in sequence_ids[:10]:  # Limit to first 10 to avoid overload
            for analysis_type in analysis_types:
                if analysis_type == "sequence_stats":
                    # Mock warming sequence stats cache
                    cache_key = f"sequence:{seq_id}"
                    tasks.append(self._warm_sequence_stats(seq_id, cache_key))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Cache warming completed")
    
    async def _warm_sequence_stats(self, sequence_id: str, cache_key: str):
        """Warm cache for sequence statistics"""
        # This is a placeholder - you would fetch actual sequence data here
        mock_stats = {
            "length": 1000,
            "gc_content": 45.2,
            "composition": {"A": 25, "T": 30, "G": 22, "C": 23}
        }
        await self._set_to_cache(cache_key, mock_stats, "sequence_stats", 3600)
    
    def cleanup_local_cache(self):
        """Clean up expired entries from local cache"""
        current_time = datetime.now()
        expired_keys = [
            key for key, value in self.local_cache.items()
            if current_time >= value["expires_at"]
        ]
        
        for key in expired_keys:
            del self.local_cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired local cache entries")
    
    async def get_cache_usage_by_namespace(self) -> Dict[str, int]:
        """Get cache usage statistics by namespace"""
        namespace_counts = {}
        
        try:
            for analysis_type, config in self.cache_config.items():
                namespace = config["namespace"]
                pattern = f"{namespace}:*"
                keys = self.redis_client.keys(pattern)
                namespace_counts[namespace] = len(keys)
        
        except Exception as e:
            logger.error(f"Error getting namespace usage: {str(e)}")
        
        return namespace_counts


# Cache decorators for common use cases
cache_manager = BioinformaticsCacheManager()

def cache_sequence_analysis(ttl: int = 3600):
    """Decorator for caching sequence analysis results"""
    return cache_manager.cached_analysis("sequence_analysis", ttl)

def cache_blast_search(ttl: int = 86400):
    """Decorator for caching BLAST search results"""  
    return cache_manager.cached_analysis("blast_search", ttl)

def cache_alignment(ttl: int = 7200):
    """Decorator for caching alignment results"""
    return cache_manager.cached_analysis("alignment", ttl)

def cache_phylogeny(ttl: int = 86400):
    """Decorator for caching phylogenetic analysis results"""
    return cache_manager.cached_analysis("phylogeny", ttl)

def cache_structure_prediction(ttl: int = 604800):
    """Decorator for caching structure prediction results"""
    return cache_manager.cached_analysis("structure_prediction", ttl)


# Usage examples in other services
class CachedAnalysisService:
    """Example service using caching"""
    
    @cache_blast_search()
    async def run_blast_search(self, sequence: str, database: str, parameters: Dict) -> Dict:
        """Cached BLAST search - this would call the actual external tool manager"""
        # This would call your ExternalToolManager.execute_blast_search method
        from .external_tool_manager import ExternalToolManager
        tool_manager = ExternalToolManager()
        return await tool_manager.execute_blast_search(sequence, database, parameters)
    
    @cache_alignment()
    async def run_multiple_alignment(self, sequences: List[str], tool: str, parameters: Dict) -> Dict:
        """Cached multiple alignment"""
        from .external_tool_manager import ExternalToolManager  
        tool_manager = ExternalToolManager()
        return await tool_manager.execute_multiple_alignment(sequences, tool, parameters)
    
    @cache_sequence_analysis()
    async def calculate_sequence_statistics(self, sequence: str) -> Dict:
        """Calculate and cache sequence statistics"""
        stats = {
            "length": len(sequence),
            "gc_content": (sequence.count('G') + sequence.count('C')) / len(sequence) * 100,
            "composition": {
                "A": sequence.count('A'),
                "T": sequence.count('T'),
                "G": sequence.count('G'),
                "C": sequence.count('C')
            },
            "molecular_weight": self._calculate_molecular_weight(sequence),
            "calculated_at": datetime.now().isoformat()
        }
        return stats
    
    def _calculate_molecular_weight(self, sequence: str) -> float:
        """Calculate approximate molecular weight"""
        # Approximate molecular weights for DNA bases
        base_weights = {"A": 331.2, "T": 322.2, "G": 347.2, "C": 307.2}
        return sum(base_weights.get(base, 0) for base in sequence.upper())