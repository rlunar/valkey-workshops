"""
Cache manager with error handling and graceful degradation.

This module provides a high-level cache abstraction layer that wraps
Valkey operations with comprehensive error handling, graceful degradation,
and performance monitoring.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import valkey
from valkey.exceptions import ConnectionError, TimeoutError, ResponseError

from .client import ValkeyClient
from .config import ValkeyConfig
from .utils import CacheKeyManager, TTLCalculator, TTLPreset, key_manager

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache operation statistics."""
    
    hit_count: int = 0
    miss_count: int = 0
    error_count: int = 0
    set_count: int = 0
    delete_count: int = 0
    total_operations: int = 0
    
    # Performance metrics
    total_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    
    # Error tracking
    connection_errors: int = 0
    timeout_errors: int = 0
    other_errors: int = 0
    
    # Degradation tracking
    degraded_operations: int = 0
    fallback_operations: int = 0
    
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total_reads = self.hit_count + self.miss_count
        return self.hit_count / total_reads if total_reads > 0 else 0.0
    
    @property
    def error_ratio(self) -> float:
        """Calculate error ratio."""
        return self.error_count / self.total_operations if self.total_operations > 0 else 0.0
    
    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time."""
        return (self.total_response_time_ms / self.total_operations 
                if self.total_operations > 0 else 0.0)
    
    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "error_count": self.error_count,
            "set_count": self.set_count,
            "delete_count": self.delete_count,
            "total_operations": self.total_operations,
            "hit_ratio": self.hit_ratio,
            "error_ratio": self.error_ratio,
            "avg_response_time_ms": self.avg_response_time_ms,
            "min_response_time_ms": self.min_response_time_ms if self.min_response_time_ms != float('inf') else 0.0,
            "max_response_time_ms": self.max_response_time_ms,
            "connection_errors": self.connection_errors,
            "timeout_errors": self.timeout_errors,
            "other_errors": self.other_errors,
            "degraded_operations": self.degraded_operations,
            "fallback_operations": self.fallback_operations,
            "uptime_seconds": self.uptime_seconds,
        }


class CacheManager:
    """
    High-level cache manager with error handling and graceful degradation.
    
    Features:
    - Automatic error handling and retry logic
    - Graceful degradation when cache is unavailable
    - Performance monitoring and statistics collection
    - Fallback mechanisms for critical operations
    - Circuit breaker pattern for failing operations
    """
    
    def __init__(
        self, 
        client: Optional[ValkeyClient] = None,
        config: Optional[ValkeyConfig] = None,
        enable_fallback: bool = True,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        """
        Initialize cache manager.
        
        Args:
            client: ValkeyClient instance
            config: ValkeyConfig for creating new client
            enable_fallback: Enable graceful degradation
            circuit_breaker_threshold: Consecutive failures before circuit opens
            circuit_breaker_timeout: Seconds to wait before retrying after circuit opens
        """
        self.client = client
        self.config = config or ValkeyConfig.from_env()
        self.enable_fallback = enable_fallback
        self.key_manager = key_manager
        self.ttl_calculator = TTLCalculator()
        
        # Statistics
        self.stats = CacheStats()
        
        # Circuit breaker
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout
        self.consecutive_failures = 0
        self.circuit_open_time: Optional[datetime] = None
        self.is_circuit_open = False
        
        # Fallback storage (in-memory cache for critical data)
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        self._fallback_max_size = 1000
        
        logger.info("CacheManager initialized with fallback enabled: %s", enable_fallback)
    
    async def initialize(self) -> None:
        """Initialize the cache manager and establish connections."""
        if not self.client:
            from .client import get_client
            self.client = await get_client(self.config)
        
        # Test connection
        try:
            await self.client.ensure_connection()
            logger.info("CacheManager successfully connected to Valkey")
        except Exception as e:
            logger.warning(f"Failed to connect to Valkey: {e}")
            if not self.enable_fallback:
                raise
    
    def _record_operation(self, operation_type: str, response_time_ms: float, success: bool = True) -> None:
        """Record operation statistics."""
        self.stats.total_operations += 1
        self.stats.total_response_time_ms += response_time_ms
        
        if response_time_ms < self.stats.min_response_time_ms:
            self.stats.min_response_time_ms = response_time_ms
        if response_time_ms > self.stats.max_response_time_ms:
            self.stats.max_response_time_ms = response_time_ms
        
        if success:
            if operation_type == "get":
                self.stats.hit_count += 1
            elif operation_type == "set":
                self.stats.set_count += 1
            elif operation_type == "delete":
                self.stats.delete_count += 1
        else:
            self.stats.error_count += 1
    
    def _record_miss(self) -> None:
        """Record cache miss."""
        self.stats.miss_count += 1
        self.stats.total_operations += 1
    
    def _record_error(self, error: Exception) -> None:
        """Record and categorize errors."""
        self.stats.error_count += 1
        self.consecutive_failures += 1
        
        if isinstance(error, ConnectionError):
            self.stats.connection_errors += 1
        elif isinstance(error, TimeoutError):
            self.stats.timeout_errors += 1
        else:
            self.stats.other_errors += 1
        
        # Check circuit breaker
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            self.is_circuit_open = True
            self.circuit_open_time = datetime.now()
            logger.warning(
                f"Circuit breaker opened after {self.consecutive_failures} consecutive failures"
            )
    
    def _record_success(self) -> None:
        """Record successful operation."""
        self.consecutive_failures = 0
        
        # Close circuit breaker if it was open
        if self.is_circuit_open:
            self.is_circuit_open = False
            self.circuit_open_time = None
            logger.info("Circuit breaker closed after successful operation")
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker should remain open."""
        if not self.is_circuit_open:
            return False
        
        if self.circuit_open_time is None:
            return False
        
        # Check if timeout has passed
        elapsed = (datetime.now() - self.circuit_open_time).total_seconds()
        if elapsed >= self.circuit_breaker_timeout:
            logger.info("Circuit breaker timeout expired, allowing retry")
            return False
        
        return True
    
    async def _execute_with_fallback(
        self,
        operation: Callable[[], Awaitable[Any]],
        fallback: Optional[Callable[[], Any]] = None,
        cache_key: Optional[str] = None
    ) -> Any:
        """
        Execute cache operation with error handling and fallback.
        
        Args:
            operation: Async function to execute
            fallback: Fallback function if operation fails
            cache_key: Cache key for fallback storage
            
        Returns:
            Operation result or fallback result
        """
        start_time = time.time()
        
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            logger.debug("Circuit breaker is open, using fallback")
            self.stats.degraded_operations += 1
            if fallback:
                return fallback()
            return None
        
        try:
            result = await operation()
            response_time_ms = (time.time() - start_time) * 1000
            self._record_success()
            return result
            
        except (ConnectionError, TimeoutError, ResponseError) as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.warning(f"Cache operation failed: {e}")
            self._record_error(e)
            
            # Try fallback
            if self.enable_fallback and fallback:
                logger.debug("Using fallback for failed cache operation")
                self.stats.fallback_operations += 1
                return fallback()
            
            # If no fallback, return None or raise based on configuration
            return None
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Unexpected error in cache operation: {e}")
            self._record_error(e)
            
            if self.enable_fallback and fallback:
                self.stats.fallback_operations += 1
                return fallback()
            
            return None
    
    def _fallback_get(self, key: str) -> Optional[Any]:
        """Get value from fallback cache."""
        if key in self._fallback_cache:
            entry = self._fallback_cache[key]
            # Check expiration
            if entry.get("expires_at") and datetime.now() > entry["expires_at"]:
                del self._fallback_cache[key]
                return None
            return entry.get("value")
        return None
    
    def _fallback_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in fallback cache."""
        # Limit fallback cache size
        if len(self._fallback_cache) >= self._fallback_max_size:
            # Remove oldest entries (simple FIFO)
            oldest_key = next(iter(self._fallback_cache))
            del self._fallback_cache[oldest_key]
        
        entry = {"value": value}
        if ttl:
            entry["expires_at"] = datetime.now() + timedelta(seconds=ttl)
        
        self._fallback_cache[key] = entry
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache with fallback support.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value, fallback value, or default
        """
        if not self.client:
            return self._fallback_get(key) or default
        
        async def cache_operation():
            try:
                await self.client.ensure_connection()
                result = self.client.client.get(key)
                if result is not None:
                    self._record_operation("get", 0, True)
                    try:
                        return json.loads(result)
                    except (json.JSONDecodeError, TypeError):
                        return result
                else:
                    self._record_miss()
                    return None
            except Exception as e:
                logger.debug(f"Cache get failed for key {key}: {e}")
                raise
        
        def fallback_operation():
            return self._fallback_get(key)
        
        result = await self._execute_with_fallback(
            cache_operation,
            fallback_operation,
            key
        )
        
        return result if result is not None else default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, TTLPreset]] = None,
        jitter: bool = True
    ) -> bool:
        """
        Set value in cache with TTL and jitter support.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds or TTLPreset
            jitter: Apply jitter to TTL to prevent clustering
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            self._fallback_set(key, value, int(ttl) if ttl else None)
            return True
        
        # Calculate TTL with jitter
        final_ttl = None
        if ttl is not None:
            base_ttl = int(ttl)
            if jitter:
                final_ttl = self.ttl_calculator.calculate_ttl_with_jitter(base_ttl)
            else:
                final_ttl = base_ttl
        
        async def cache_operation():
            try:
                await self.client.ensure_connection()
                
                # Serialize value
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value)
                else:
                    serialized_value = str(value)
                
                if final_ttl:
                    result = self.client.client.setex(key, final_ttl, serialized_value)
                else:
                    result = self.client.client.set(key, serialized_value)
                
                self._record_operation("set", 0, True)
                return bool(result)
                
            except Exception as e:
                logger.debug(f"Cache set failed for key {key}: {e}")
                raise
        
        def fallback_operation():
            self._fallback_set(key, value, final_ttl)
            return True
        
        result = await self._execute_with_fallback(
            cache_operation,
            fallback_operation,
            key
        )
        
        return bool(result)
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self.client:
            if key in self._fallback_cache:
                del self._fallback_cache[key]
                return True
            return False
        
        async def cache_operation():
            try:
                await self.client.ensure_connection()
                result = self.client.client.delete(key)
                self._record_operation("delete", 0, True)
                return bool(result)
            except Exception as e:
                logger.debug(f"Cache delete failed for key {key}: {e}")
                raise
        
        def fallback_operation():
            if key in self._fallback_cache:
                del self._fallback_cache[key]
                return True
            return False
        
        result = await self._execute_with_fallback(
            cache_operation,
            fallback_operation,
            key
        )
        
        return bool(result)
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.client:
            return key in self._fallback_cache
        
        async def cache_operation():
            try:
                await self.client.ensure_connection()
                result = self.client.client.exists(key)
                return bool(result)
            except Exception as e:
                logger.debug(f"Cache exists check failed for key {key}: {e}")
                raise
        
        def fallback_operation():
            return key in self._fallback_cache
        
        result = await self._execute_with_fallback(
            cache_operation,
            fallback_operation,
            key
        )
        
        return bool(result)
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for key.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining TTL in seconds, None if key doesn't exist or no TTL
        """
        if not self.client:
            if key in self._fallback_cache:
                entry = self._fallback_cache[key]
                if "expires_at" in entry:
                    remaining = (entry["expires_at"] - datetime.now()).total_seconds()
                    return max(0, int(remaining))
            return None
        
        async def cache_operation():
            try:
                await self.client.ensure_connection()
                result = self.client.client.ttl(key)
                return result if result > 0 else None
            except Exception as e:
                logger.debug(f"Cache TTL check failed for key {key}: {e}")
                raise
        
        result = await self._execute_with_fallback(cache_operation)
        return result
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
            
        Returns:
            Number of keys deleted
        """
        if not self.client:
            # Simple pattern matching for fallback cache
            import fnmatch
            deleted = 0
            keys_to_delete = []
            for key in self._fallback_cache:
                if fnmatch.fnmatch(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self._fallback_cache[key]
                deleted += 1
            
            return deleted
        
        async def cache_operation():
            try:
                await self.client.ensure_connection()
                
                # Use SCAN to find matching keys
                keys = []
                for key in self.client.client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    deleted = self.client.client.delete(*keys)
                    return deleted
                return 0
                
            except Exception as e:
                logger.debug(f"Cache pattern clear failed for pattern {pattern}: {e}")
                raise
        
        result = await self._execute_with_fallback(cache_operation)
        return result or 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache manager statistics.
        
        Returns:
            Dict containing performance and error statistics
        """
        stats = self.stats.to_dict()
        
        # Add circuit breaker info
        stats.update({
            "circuit_breaker_open": self.is_circuit_open,
            "consecutive_failures": self.consecutive_failures,
            "fallback_enabled": self.enable_fallback,
            "fallback_cache_size": len(self._fallback_cache),
        })
        
        # Add connection info if available
        if self.client:
            try:
                connection_info = await self.client.get_connection_info()
                stats["connection_info"] = connection_info
            except Exception as e:
                stats["connection_error"] = str(e)
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Dict containing health status and diagnostics
        """
        health = {
            "status": "unknown",
            "cache_available": False,
            "fallback_active": False,
            "circuit_breaker_open": self.is_circuit_open,
            "errors": [],
        }
        
        if not self.client:
            health.update({
                "status": "degraded",
                "fallback_active": True,
                "errors": ["No Valkey client available"],
            })
            return health
        
        try:
            # Test basic operations
            test_key = "health_check_test"
            test_value = {"timestamp": datetime.now().isoformat()}
            
            # Test set
            await self.set(test_key, test_value, ttl=60)
            
            # Test get
            retrieved = await self.get(test_key)
            
            # Test delete
            await self.delete(test_key)
            
            if retrieved:
                health.update({
                    "status": "healthy",
                    "cache_available": True,
                })
            else:
                health.update({
                    "status": "degraded",
                    "cache_available": False,
                    "fallback_active": self.enable_fallback,
                    "errors": ["Cache operations not working properly"],
                })
        
        except Exception as e:
            health.update({
                "status": "unhealthy" if not self.enable_fallback else "degraded",
                "cache_available": False,
                "fallback_active": self.enable_fallback,
                "errors": [str(e)],
            })
        
        return health
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for cache transactions (if supported).
        
        Note: This is a placeholder for future transaction support.
        Currently just ensures connection.
        """
        if self.client:
            await self.client.ensure_connection()
        
        try:
            yield self
        except Exception as e:
            logger.error(f"Error in cache transaction: {e}")
            raise
    
    async def close(self) -> None:
        """Close cache manager and cleanup resources."""
        if self.client:
            await self.client.disconnect()
        
        # Clear fallback cache
        self._fallback_cache.clear()
        
        logger.info("CacheManager closed")


# Global cache manager instance
_global_cache_manager: Optional[CacheManager] = None


async def get_cache_manager(
    client: Optional[ValkeyClient] = None,
    config: Optional[ValkeyConfig] = None,
    **kwargs
) -> CacheManager:
    """
    Get or create global cache manager instance.
    
    Args:
        client: Optional ValkeyClient instance
        config: Optional ValkeyConfig
        **kwargs: Additional CacheManager arguments
        
    Returns:
        CacheManager: Global cache manager instance
    """
    global _global_cache_manager
    
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager(client=client, config=config, **kwargs)
        await _global_cache_manager.initialize()
    
    return _global_cache_manager


async def close_global_cache_manager() -> None:
    """Close the global cache manager."""
    global _global_cache_manager
    
    if _global_cache_manager:
        await _global_cache_manager.close()
        _global_cache_manager = None