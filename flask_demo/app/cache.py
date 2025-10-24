"""Cache management utilities for the Flask caching demo."""

import time
import re
from functools import wraps
from flask import current_app
from app import flask_cache as cache


class CacheManager:
    """Centralized cache management with various caching strategies."""
    
    def __init__(self):
        """Initialize cache manager with statistics tracking."""
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
    
    def get_or_set(self, key, callable_func, timeout=300):
        """
        Cache-aside pattern implementation with statistics tracking.
        
        Args:
            key: Cache key
            callable_func: Function to call if cache miss
            timeout: Cache timeout in seconds
            
        Returns:
            Cached or freshly computed value
        """
        try:
            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                self._stats['hits'] += 1
                current_app.logger.debug(f"Cache hit for key: {key}")
                return cached_value
            
            # Cache miss - compute value
            self._stats['misses'] += 1
            current_app.logger.debug(f"Cache miss for key: {key}")
            value = callable_func()
            
            # Store in cache
            cache.set(key, value, timeout=timeout)
            self._stats['sets'] += 1
            current_app.logger.debug(f"Cache set for key: {key}")
            return value
            
        except Exception as e:
            self._stats['errors'] += 1
            current_app.logger.error(f"Cache error for key {key}: {e}")
            # Fallback to direct computation
            return callable_func()
    
    def invalidate(self, pattern):
        """
        Invalidate cache keys matching a pattern.
        
        Args:
            pattern: Pattern to match cache keys (supports wildcards)
        """
        try:
            if hasattr(cache.cache, '_write_client'):
                # Redis/Valkey backend - use pattern matching
                redis_client = cache.cache._write_client
                keys = redis_client.keys(pattern)
                if keys:
                    deleted_count = redis_client.delete(*keys)
                    self._stats['deletes'] += deleted_count
                    current_app.logger.info(f"Invalidated {deleted_count} keys matching pattern: {pattern}")
                    return deleted_count
                else:
                    current_app.logger.info(f"No keys found matching pattern: {pattern}")
                    return 0
            else:
                # Fallback for other cache backends
                cache.clear()
                self._stats['deletes'] += 1
                current_app.logger.info(f"Cache cleared (pattern matching not supported): {pattern}")
                return 1
                
        except Exception as e:
            self._stats['errors'] += 1
            current_app.logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0
    
    def invalidate_key(self, key):
        """
        Invalidate a specific cache key.
        
        Args:
            key: Specific cache key to invalidate
            
        Returns:
            bool: True if key was deleted, False otherwise
        """
        try:
            result = cache.delete(key)
            if result:
                self._stats['deletes'] += 1
                current_app.logger.debug(f"Invalidated cache key: {key}")
            return result
        except Exception as e:
            self._stats['errors'] += 1
            current_app.logger.error(f"Error invalidating key {key}: {e}")
            return False
    
    def get_stats(self):
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics and performance metrics
        """
        try:
            total_operations = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_operations * 100) if total_operations > 0 else 0
            
            base_stats = {
                'cache_type': current_app.config.get('CACHE_TYPE', 'unknown'),
                'default_timeout': current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300),
                'key_prefix': current_app.config.get('CACHE_KEY_PREFIX', ''),
                'status': 'connected'
            }
            
            performance_stats = {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'sets': self._stats['sets'],
                'deletes': self._stats['deletes'],
                'errors': self._stats['errors'],
                'hit_rate': round(hit_rate, 2),
                'total_operations': total_operations
            }
            
            # Try to get additional Redis/Valkey stats if available
            if hasattr(cache.cache, '_write_client'):
                try:
                    redis_client = cache.cache._write_client
                    redis_info = redis_client.info('memory')
                    performance_stats.update({
                        'memory_used': redis_info.get('used_memory_human', 'N/A'),
                        'memory_peak': redis_info.get('used_memory_peak_human', 'N/A'),
                        'keyspace_hits': redis_info.get('keyspace_hits', 0),
                        'keyspace_misses': redis_info.get('keyspace_misses', 0)
                    })
                except Exception:
                    pass  # Redis stats not available
            
            return {**base_stats, **performance_stats}
            
        except Exception as e:
            current_app.logger.error(f"Error getting cache stats: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def reset_stats(self):
        """Reset internal statistics counters."""
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        current_app.logger.info("Cache statistics reset")
    
    def set_with_expiry(self, key, value, timeout=None):
        """
        Set cache value with time-based expiration.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Expiration time in seconds (None for default)
        """
        try:
            if timeout is None:
                timeout = current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
            
            cache.set(key, value, timeout=timeout)
            self._stats['sets'] += 1
            current_app.logger.debug(f"Cache set with expiry {timeout}s for key: {key}")
            return True
        except Exception as e:
            self._stats['errors'] += 1
            current_app.logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def write_through(self, key, value, update_func, timeout=300):
        """
        Write-through caching: update both cache and data source.
        
        Args:
            key: Cache key
            value: New value
            update_func: Function to update the data source
            timeout: Cache timeout in seconds
            
        Returns:
            bool: True if both cache and data source were updated successfully
        """
        try:
            # First update the data source
            update_result = update_func(value)
            
            if update_result:
                # If data source update succeeded, update cache
                cache.set(key, value, timeout=timeout)
                self._stats['sets'] += 1
                current_app.logger.debug(f"Write-through cache update for key: {key}")
                return True
            else:
                current_app.logger.warning(f"Data source update failed for key: {key}")
                return False
                
        except Exception as e:
            self._stats['errors'] += 1
            current_app.logger.error(f"Write-through cache error for key {key}: {e}")
            return False
    
    def warm_cache(self, data_source_func, key_generator_func, timeout=300, batch_size=100):
        """
        Cache warming: preload frequently accessed data.
        
        Args:
            data_source_func: Function that returns data to cache
            key_generator_func: Function that generates cache keys for data items
            timeout: Cache timeout in seconds
            batch_size: Number of items to process in each batch
            
        Returns:
            dict: Statistics about the warming process
        """
        warming_stats = {
            'items_processed': 0,
            'items_cached': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        try:
            current_app.logger.info("Starting cache warming process")
            
            # Get data from source
            data_items = data_source_func()
            
            # Process in batches
            for i in range(0, len(data_items), batch_size):
                batch = data_items[i:i + batch_size]
                
                for item in batch:
                    try:
                        cache_key = key_generator_func(item)
                        cache.set(cache_key, item, timeout=timeout)
                        warming_stats['items_cached'] += 1
                        self._stats['sets'] += 1
                    except Exception as e:
                        warming_stats['errors'] += 1
                        current_app.logger.error(f"Error warming cache for item: {e}")
                    
                    warming_stats['items_processed'] += 1
            
            warming_stats['duration'] = time.time() - warming_stats['start_time']
            current_app.logger.info(
                f"Cache warming completed: {warming_stats['items_cached']} items cached, "
                f"{warming_stats['errors']} errors, {warming_stats['duration']:.2f}s"
            )
            
            return warming_stats
            
        except Exception as e:
            self._stats['errors'] += 1
            warming_stats['errors'] += 1
            warming_stats['duration'] = time.time() - warming_stats['start_time']
            current_app.logger.error(f"Cache warming failed: {e}")
            return warming_stats
    
    def get_with_refresh(self, key, callable_func, timeout=300, refresh_threshold=0.8):
        """
        Get cached value with proactive refresh before expiration.
        
        Args:
            key: Cache key
            callable_func: Function to call for refresh
            timeout: Cache timeout in seconds
            refresh_threshold: Refresh when TTL falls below this fraction of timeout
            
        Returns:
            Cached or refreshed value
        """
        try:
            cached_value = cache.get(key)
            
            if cached_value is not None:
                self._stats['hits'] += 1
                
                # Check if we should proactively refresh
                if hasattr(cache.cache, '_write_client'):
                    try:
                        redis_client = cache.cache._write_client
                        ttl = redis_client.ttl(key)
                        
                        if ttl > 0 and ttl < (timeout * refresh_threshold):
                            # Proactively refresh in background
                            try:
                                new_value = callable_func()
                                cache.set(key, new_value, timeout=timeout)
                                self._stats['sets'] += 1
                                current_app.logger.debug(f"Proactive cache refresh for key: {key}")
                                return new_value
                            except Exception:
                                # If refresh fails, return cached value
                                pass
                    except Exception:
                        # TTL check failed, continue with cached value
                        pass
                
                return cached_value
            
            # Cache miss - compute and store
            self._stats['misses'] += 1
            value = callable_func()
            cache.set(key, value, timeout=timeout)
            self._stats['sets'] += 1
            return value
            
        except Exception as e:
            self._stats['errors'] += 1
            current_app.logger.error(f"Cache refresh error for key {key}: {e}")
            return callable_func()


# Global cache manager instance
cache_manager = CacheManager()


def cached_route(timeout=300, key_prefix='route'):
    """
    Decorator for caching route responses.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache keys
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key based on route and arguments
            cache_key = f"{key_prefix}:{f.__name__}:{hash(str(args) + str(kwargs))}"
            
            return cache_manager.get_or_set(
                cache_key,
                lambda: f(*args, **kwargs),
                timeout=timeout
            )
        return decorated_function
    return decorator


def cached_function(timeout=300, key_prefix='func'):
    """
    Decorator for caching function results with time-based expiration.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache keys
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key based on function name and arguments
            args_str = str(args) + str(sorted(kwargs.items()))
            cache_key = f"{key_prefix}:{f.__name__}:{hash(args_str)}"
            
            return cache_manager.get_or_set(
                cache_key,
                lambda: f(*args, **kwargs),
                timeout=timeout
            )
        return decorated_function
    return decorator


def cache_warming_decorator(key_generator, timeout=300):
    """
    Decorator that enables cache warming for functions.
    
    Args:
        key_generator: Function to generate cache key from function args
        timeout: Cache timeout in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key_generator(*args, **kwargs)
            
            return cache_manager.get_with_refresh(
                cache_key,
                lambda: f(*args, **kwargs),
                timeout=timeout
            )
        return decorated_function
    return decorator


class CacheStrategies:
    """Collection of common caching strategies and utilities."""
    
    @staticmethod
    def time_based_cache(key, value, minutes=5):
        """Cache with time-based expiration in minutes."""
        return cache_manager.set_with_expiry(key, value, timeout=minutes * 60)
    
    @staticmethod
    def short_term_cache(key, value):
        """Cache for short-term use (1 minute)."""
        return cache_manager.set_with_expiry(key, value, timeout=60)
    
    @staticmethod
    def medium_term_cache(key, value):
        """Cache for medium-term use (15 minutes)."""
        return cache_manager.set_with_expiry(key, value, timeout=900)
    
    @staticmethod
    def long_term_cache(key, value):
        """Cache for long-term use (1 hour)."""
        return cache_manager.set_with_expiry(key, value, timeout=3600)
    
    @staticmethod
    def invalidate_related_caches(base_pattern):
        """Invalidate all caches matching a base pattern."""
        patterns = [
            f"{base_pattern}:*",
            f"route:*{base_pattern}*",
            f"func:*{base_pattern}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = cache_manager.invalidate(pattern)
            total_deleted += deleted
        
        return total_deleted