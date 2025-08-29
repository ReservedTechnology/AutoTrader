"""
Redis Manager for caching and queue operations
Provides centralized Redis connection management
"""
import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Centralized Redis connection and operations manager
    Falls back to in-memory operations when Redis is unavailable
    """
    
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
        self._memory_cache = {}
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Redis connection with fallback to memory cache"""
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            # Try importing redis
            import redis
            
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.is_connected = True
            logger.info(f"✅ Redis connected at {redis_url}")
            
        except ImportError:
            logger.warning("⚠️  Redis library not installed, using memory cache")
            self.is_connected = False
            
        except Exception as e:
            logger.warning(f"⚠️  Redis not available ({e}), using memory cache")
            self.is_connected = False
    
    def set_price(self, symbol: str, price_data: Dict[str, Any], ttl_seconds: int = 300) -> bool:
        """
        Cache price data with TTL
        
        Args:
            symbol: Currency pair symbol
            price_data: Price information dictionary
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_entry = {
                'data': price_data,
                'timestamp': datetime.now().isoformat(),
                'ttl': ttl_seconds
            }
            
            if self.is_connected and self.redis_client:
                # Use Redis
                key = f"forex:price:{symbol}"
                self.redis_client.setex(
                    key,
                    ttl_seconds,
                    json.dumps(cache_entry, default=str)
                )
                return True
            else:
                # Use memory cache
                self._memory_cache[f"forex:price:{symbol}"] = {
                    **cache_entry,
                    'expires_at': datetime.now() + timedelta(seconds=ttl_seconds)
                }
                return True
                
        except Exception as e:
            logger.error(f"Error caching price for {symbol}: {e}")
            return False
    
    def get_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached price data
        
        Args:
            symbol: Currency pair symbol
            
        Returns:
            Price data or None if not found/expired
        """
        try:
            key = f"forex:price:{symbol}"
            
            if self.is_connected and self.redis_client:
                # Use Redis
                cached_data = self.redis_client.get(key)
                if cached_data:
                    return json.loads(cached_data)['data']
            else:
                # Use memory cache
                if key in self._memory_cache:
                    entry = self._memory_cache[key]
                    if datetime.now() < entry['expires_at']:
                        return entry['data']
                    else:
                        # Remove expired entry
                        del self._memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving price for {symbol}: {e}")
            return None
    
    def set_trading_signal(self, signal_id: str, signal_data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """
        Cache trading signal
        
        Args:
            signal_id: Unique signal identifier
            signal_data: Signal information
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            key = f"trading:signal:{signal_id}"
            cache_entry = {
                'signal': signal_data,
                'created_at': datetime.now().isoformat()
            }
            
            if self.is_connected and self.redis_client:
                self.redis_client.setex(
                    key,
                    ttl_seconds,
                    json.dumps(cache_entry, default=str)
                )
            else:
                self._memory_cache[key] = {
                    **cache_entry,
                    'expires_at': datetime.now() + timedelta(seconds=ttl_seconds)
                }
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching trading signal {signal_id}: {e}")
            return False
    
    def get_active_signals(self, strategy: str = None) -> List[Dict[str, Any]]:
        """
        Get all active trading signals, optionally filtered by strategy
        
        Args:
            strategy: Strategy name to filter by
            
        Returns:
            List of active signals
        """
        try:
            signals = []
            
            if self.is_connected and self.redis_client:
                # Use Redis
                pattern = "trading:signal:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    signal_data = self.redis_client.get(key)
                    if signal_data:
                        signal = json.loads(signal_data)['signal']
                        if not strategy or signal.get('strategy') == strategy:
                            signals.append(signal)
            else:
                # Use memory cache
                now = datetime.now()
                for key, entry in list(self._memory_cache.items()):
                    if key.startswith("trading:signal:"):
                        if now < entry['expires_at']:
                            signal = entry['signal']
                            if not strategy or signal.get('strategy') == strategy:
                                signals.append(signal)
                        else:
                            del self._memory_cache[key]
            
            return signals
            
        except Exception as e:
            logger.error(f"Error retrieving active signals: {e}")
            return []
    
    def increment_counter(self, counter_name: str, expiry_seconds: int = 86400) -> int:
        """
        Increment a counter with expiry
        
        Args:
            counter_name: Name of the counter
            expiry_seconds: Expiry time in seconds
            
        Returns:
            New counter value
        """
        try:
            key = f"counter:{counter_name}"
            
            if self.is_connected and self.redis_client:
                # Use Redis atomic increment
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, expiry_seconds)
                results = pipe.execute()
                return results[0]
            else:
                # Use memory cache
                if key not in self._memory_cache:
                    self._memory_cache[key] = {
                        'value': 0,
                        'expires_at': datetime.now() + timedelta(seconds=expiry_seconds)
                    }
                
                entry = self._memory_cache[key]
                if datetime.now() < entry['expires_at']:
                    entry['value'] += 1
                    return entry['value']
                else:
                    # Reset expired counter
                    self._memory_cache[key] = {
                        'value': 1,
                        'expires_at': datetime.now() + timedelta(seconds=expiry_seconds)
                    }
                    return 1
                    
        except Exception as e:
            logger.error(f"Error incrementing counter {counter_name}: {e}")
            return 1
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get Redis health status and statistics
        
        Returns:
            Health status dictionary
        """
        try:
            status = {
                'redis_connected': self.is_connected,
                'cache_type': 'redis' if self.is_connected else 'memory',
                'memory_cache_size': len(self._memory_cache)
            }
            
            if self.is_connected and self.redis_client:
                info = self.redis_client.info()
                status.update({
                    'redis_version': info.get('redis_version'),
                    'used_memory': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                })
                
                # Calculate hit rate
                hits = info.get('keyspace_hits', 0)
                misses = info.get('keyspace_misses', 0)
                total = hits + misses
                status['hit_rate'] = hits / total if total > 0 else 0
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting Redis health status: {e}")
            return {
                'redis_connected': False,
                'cache_type': 'memory',
                'error': str(e),
                'memory_cache_size': len(self._memory_cache)
            }
    
    def clear_cache(self, pattern: str = None) -> bool:
        """
        Clear cache entries
        
        Args:
            pattern: Pattern to match keys (e.g., 'forex:*')
            
        Returns:
            True if successful
        """
        try:
            if self.is_connected and self.redis_client:
                if pattern:
                    keys = list(self.redis_client.scan_iter(match=pattern))
                    if keys:
                        self.redis_client.delete(*keys)
                else:
                    self.redis_client.flushdb()
            else:
                if pattern:
                    # Simple pattern matching for memory cache
                    keys_to_remove = [
                        key for key in self._memory_cache.keys()
                        if pattern.replace('*', '') in key
                    ]
                    for key in keys_to_remove:
                        del self._memory_cache[key]
                else:
                    self._memory_cache.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# Global Redis manager instance
redis_manager = RedisManager()
