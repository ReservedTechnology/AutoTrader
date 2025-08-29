"""
Price Cache Implementation with Redis backend
Handles caching of forex price data for fast retrieval
"""
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import redis
import aioredis
import os
import logging

logger = logging.getLogger(__name__)


class PriceCache:
    """
    Redis-backed price cache for forex data
    Provides TTL-based caching with LRU eviction
    """
    
    def __init__(self, ttl_ms: int = 5000, max_size: int = 1000):
        """
        Initialize price cache
        
        Args:
            ttl_ms: Time to live in milliseconds
            max_size: Maximum number of items in cache
        """
        self.ttl_ms = ttl_ms
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        
        # Redis connection setup
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Test connection
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis_client = None
            self._memory_cache = {}
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Store price data in cache
        
        Args:
            key: Price symbol (e.g., 'EUR_USD')
            value: Price data dictionary
        """
        try:
            if self.redis_client:
                # Use Redis
                cache_data = {
                    'data': value,
                    'timestamp': time.time() * 1000  # Convert to milliseconds
                }
                
                # Store with TTL
                self.redis_client.setex(
                    f"price:{key}",
                    int(self.ttl_ms / 1000),  # Redis TTL in seconds
                    json.dumps(cache_data, default=str)
                )
                
                # Maintain cache size limit
                self._enforce_size_limit()
            else:
                # Use in-memory cache
                self._memory_cache[key] = {
                    'data': value,
                    'timestamp': time.time() * 1000,
                    'access_time': time.time()
                }
                self._enforce_memory_size_limit()
                
        except Exception as e:
            logger.error(f"Error setting cache value for {key}: {e}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve price data from cache
        
        Args:
            key: Price symbol
            
        Returns:
            Price data dictionary or None if not found/expired
        """
        try:
            if self.redis_client:
                # Use Redis
                cached = self.redis_client.get(f"price:{key}")
                if cached:
                    cache_data = json.loads(cached)
                    
                    # Check if expired
                    age_ms = time.time() * 1000 - cache_data['timestamp']
                    if age_ms <= self.ttl_ms:
                        self.hits += 1
                        return cache_data['data']
                    else:
                        # Remove expired entry
                        self.redis_client.delete(f"price:{key}")
            else:
                # Use in-memory cache
                if key in self._memory_cache:
                    cache_entry = self._memory_cache[key]
                    age_ms = time.time() * 1000 - cache_entry['timestamp']
                    
                    if age_ms <= self.ttl_ms:
                        # Update access time for LRU
                        cache_entry['access_time'] = time.time()
                        self.hits += 1
                        return cache_entry['data']
                    else:
                        # Remove expired entry
                        del self._memory_cache[key]
            
            self.misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache value for {key}: {e}")
            self.misses += 1
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics
        
        Returns:
            Dictionary with hit rate, miss rate, size, etc.
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        if self.redis_client:
            try:
                # Count keys in Redis
                size = len(self.redis_client.keys("price:*"))
            except:
                size = 0
        else:
            size = len(self._memory_cache)
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': size,
            'max_size': self.max_size,
            'ttl_ms': self.ttl_ms
        }
    
    def clear(self) -> None:
        """Clear all cache entries"""
        try:
            if self.redis_client:
                # Delete all price keys
                keys = self.redis_client.keys("price:*")
                if keys:
                    self.redis_client.delete(*keys)
            else:
                self._memory_cache.clear()
                
            self.hits = 0
            self.misses = 0
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def _enforce_size_limit(self) -> None:
        """Enforce max size limit for Redis cache"""
        if not self.redis_client:
            return
            
        try:
            keys = self.redis_client.keys("price:*")
            if len(keys) > self.max_size:
                # Remove oldest keys (simple approach)
                # In production, consider using Redis EXPIRE with shorter TTL
                excess_count = len(keys) - self.max_size
                keys_to_remove = keys[:excess_count]
                if keys_to_remove:
                    self.redis_client.delete(*keys_to_remove)
        except Exception as e:
            logger.error(f"Error enforcing Redis size limit: {e}")
    
    def _enforce_memory_size_limit(self) -> None:
        """Enforce max size limit for in-memory cache using LRU"""
        if len(self._memory_cache) > self.max_size:
            # Remove least recently used items
            sorted_items = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1]['access_time']
            )
            
            # Remove oldest items
            excess_count = len(self._memory_cache) - self.max_size
            for i in range(excess_count):
                key_to_remove = sorted_items[i][0]
                del self._memory_cache[key_to_remove]


class AsyncPriceCache:
    """
    Async version of PriceCache using aioredis
    """
    
    def __init__(self, ttl_ms: int = 5000, max_size: int = 1000):
        self.ttl_ms = ttl_ms
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.redis_pool = None
        self._memory_cache = {}
    
    async def initialize(self):
        """Initialize async Redis connection"""
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.redis_pool = aioredis.from_url(redis_url, decode_responses=True)
            await self.redis_pool.ping()
            logger.info(f"Connected to Redis (async) at {redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis_pool = None
    
    async def set(self, key: str, value: Dict[str, Any]) -> None:
        """Async version of set"""
        try:
            if self.redis_pool:
                cache_data = {
                    'data': value,
                    'timestamp': time.time() * 1000
                }
                
                await self.redis_pool.setex(
                    f"price:{key}",
                    int(self.ttl_ms / 1000),
                    json.dumps(cache_data, default=str)
                )
            else:
                self._memory_cache[key] = {
                    'data': value,
                    'timestamp': time.time() * 1000,
                    'access_time': time.time()
                }
                self._enforce_memory_size_limit()
                
        except Exception as e:
            logger.error(f"Error setting async cache value for {key}: {e}")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Async version of get"""
        try:
            if self.redis_pool:
                cached = await self.redis_pool.get(f"price:{key}")
                if cached:
                    cache_data = json.loads(cached)
                    age_ms = time.time() * 1000 - cache_data['timestamp']
                    
                    if age_ms <= self.ttl_ms:
                        self.hits += 1
                        return cache_data['data']
                    else:
                        await self.redis_pool.delete(f"price:{key}")
            else:
                # Use sync logic for memory cache
                if key in self._memory_cache:
                    cache_entry = self._memory_cache[key]
                    age_ms = time.time() * 1000 - cache_entry['timestamp']
                    
                    if age_ms <= self.ttl_ms:
                        cache_entry['access_time'] = time.time()
                        self.hits += 1
                        return cache_entry['data']
                    else:
                        del self._memory_cache[key]
            
            self.misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting async cache value for {key}: {e}")
            self.misses += 1
            return None
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_pool:
            await self.redis_pool.close()
    
    def _enforce_memory_size_limit(self):
        """Same as sync version"""
        if len(self._memory_cache) > self.max_size:
            sorted_items = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1]['access_time']
            )
            
            excess_count = len(self._memory_cache) - self.max_size
            for i in range(excess_count):
                key_to_remove = sorted_items[i][0]
                del self._memory_cache[key_to_remove]


# Global cache instance
price_cache = PriceCache()
