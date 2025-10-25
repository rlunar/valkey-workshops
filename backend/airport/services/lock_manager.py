"""
Distributed lock manager for cache stampede prevention.

This module implements distributed locking using Valkey SET with NX and EX options
to prevent cache stampede scenarios and coordinate cache warming strategies.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from ..cache.manager import CacheManager
from ..cache.utils import key_manager

logger = logging.getLogger(__name__)


@dataclass
class LockInfo:
    """Information about a distributed lock."""
    lock_key: str
    lock_value: str
    acquired_at: datetime
    expires_at: datetime
    ttl_seconds: int
    owner_id: str
    
    @property
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        return datetime.now() > self.expires_at
    
    @property
    def remaining_ttl_seconds(self) -> float:
        """Get remaining TTL in seconds."""
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0.0, remaining)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert lock info to dictionary."""
        return {
            "lock_key": self.lock_key,
            "lock_value": self.lock_value,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "owner_id": self.owner_id,
            "is_expired": self.is_expired,
            "remaining_ttl_seconds": self.remaining_ttl_seconds
        }


@dataclass
class StampedePreventionMetrics:
    """Metrics for cache stampede prevention."""
    operation_type: str
    cache_key: str
    lock_acquired: bool
    lock_wait_time_ms: float
    total_execution_time_ms: float
    concurrent_requests: int = 0
    cache_rebuild_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "operation_type": self.operation_type,
            "cache_key": self.cache_key,
            "lock_acquired": self.lock_acquired,
            "lock_wait_time_ms": self.lock_wait_time_ms,
            "total_execution_time_ms": self.total_execution_time_ms,
            "concurrent_requests": self.concurrent_requests,
            "cache_rebuild_time_ms": self.cache_rebuild_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class DistributedLockManager:
    """
    Distributed lock manager using Valkey SET with NX and EX options.
    
    Features:
    - Atomic lock acquisition with TTL
    - Lock renewal and extension
    - Deadlock prevention with automatic expiration
    - Cache stampede prevention patterns
    - Lock contention monitoring and metrics
    """
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize distributed lock manager.
        
        Args:
            cache_manager: CacheManager instance for lock operations
        """
        self.cache = cache_manager
        self.instance_id = str(uuid.uuid4())[:8]  # Unique instance identifier
        self.active_locks: Dict[str, LockInfo] = {}
        self.metrics: List[StampedePreventionMetrics] = []
        
        # Default lock configuration
        self.default_lock_ttl = 30  # 30 seconds default TTL
        self.max_lock_ttl = 300     # 5 minutes maximum TTL
        self.lock_retry_delay = 0.1 # 100ms between retry attempts
        self.max_retry_attempts = 50 # Maximum retry attempts
        
        logger.info(f"DistributedLockManager initialized with instance ID: {self.instance_id}")
    
    async def acquire_lock(
        self, 
        resource_key: str, 
        ttl_seconds: int = None,
        timeout_seconds: float = 5.0,
        retry_delay: float = None
    ) -> Optional[LockInfo]:
        """
        Acquire a distributed lock for the given resource.
        
        Args:
            resource_key: Resource identifier to lock
            ttl_seconds: Lock TTL in seconds (default: 30)
            timeout_seconds: Maximum time to wait for lock acquisition
            retry_delay: Delay between retry attempts
            
        Returns:
            LockInfo if lock acquired, None if timeout or failure
        """
        ttl = ttl_seconds or self.default_lock_ttl
        ttl = min(ttl, self.max_lock_ttl)  # Enforce maximum TTL
        retry_delay = retry_delay or self.lock_retry_delay
        
        lock_key = key_manager.key_builder.build_key("lock", resource_key)
        lock_value = f"{self.instance_id}:{uuid.uuid4()}"
        
        start_time = time.time()
        attempts = 0
        max_attempts = int(timeout_seconds / retry_delay)
        
        while attempts < max_attempts and attempts < self.max_retry_attempts:
            try:
                # Try to acquire lock using SET NX EX
                if not self.cache.client:
                    await self.cache.initialize()
                
                await self.cache.client.ensure_connection()
                
                # Use SET with NX (only set if not exists) and EX (expiration)
                result = self.cache.client.client.set(
                    lock_key, 
                    lock_value, 
                    nx=True,  # Only set if key doesn't exist
                    ex=ttl    # Set expiration time
                )
                
                if result:
                    # Lock acquired successfully
                    acquired_at = datetime.now()
                    expires_at = acquired_at + timedelta(seconds=ttl)
                    
                    lock_info = LockInfo(
                        lock_key=lock_key,
                        lock_value=lock_value,
                        acquired_at=acquired_at,
                        expires_at=expires_at,
                        ttl_seconds=ttl,
                        owner_id=self.instance_id
                    )
                    
                    # Store in active locks
                    self.active_locks[lock_key] = lock_info
                    
                    wait_time_ms = (time.time() - start_time) * 1000
                    logger.debug(f"Lock acquired: {lock_key} (attempts: {attempts + 1}, wait: {wait_time_ms:.1f}ms)")
                    
                    return lock_info
                
                # Lock not acquired, wait and retry
                attempts += 1
                if attempts < max_attempts:
                    await asyncio.sleep(retry_delay)
                
            except Exception as e:
                logger.warning(f"Error acquiring lock {lock_key}: {e}")
                attempts += 1
                if attempts < max_attempts:
                    await asyncio.sleep(retry_delay)
        
        # Lock acquisition failed
        wait_time_ms = (time.time() - start_time) * 1000
        logger.warning(f"Failed to acquire lock: {lock_key} (attempts: {attempts}, wait: {wait_time_ms:.1f}ms)")
        
        return None
    
    async def release_lock(self, lock_info: LockInfo) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_info: Lock information from acquire_lock
            
        Returns:
            True if lock was released, False otherwise
        """
        try:
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Use Lua script to ensure atomic release (only if we own the lock)
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            # Execute Lua script
            result = self.cache.client.client.eval(
                lua_script, 
                1, 
                lock_info.lock_key, 
                lock_info.lock_value
            )
            
            # Remove from active locks
            if lock_info.lock_key in self.active_locks:
                del self.active_locks[lock_info.lock_key]
            
            success = bool(result)
            if success:
                logger.debug(f"Lock released: {lock_info.lock_key}")
            else:
                logger.warning(f"Lock release failed (not owner): {lock_info.lock_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error releasing lock {lock_info.lock_key}: {e}")
            return False
    
    async def extend_lock(self, lock_info: LockInfo, additional_ttl: int) -> bool:
        """
        Extend the TTL of an existing lock.
        
        Args:
            lock_info: Lock information from acquire_lock
            additional_ttl: Additional seconds to add to TTL
            
        Returns:
            True if lock was extended, False otherwise
        """
        try:
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Use Lua script to extend TTL only if we own the lock
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            
            new_ttl = lock_info.ttl_seconds + additional_ttl
            new_ttl = min(new_ttl, self.max_lock_ttl)  # Enforce maximum TTL
            
            result = self.cache.client.client.eval(
                lua_script,
                1,
                lock_info.lock_key,
                lock_info.lock_value,
                new_ttl
            )
            
            if result:
                # Update lock info
                lock_info.ttl_seconds = new_ttl
                lock_info.expires_at = datetime.now() + timedelta(seconds=new_ttl)
                
                logger.debug(f"Lock extended: {lock_info.lock_key} (new TTL: {new_ttl}s)")
                return True
            else:
                logger.warning(f"Lock extension failed (not owner): {lock_info.lock_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error extending lock {lock_info.lock_key}: {e}")
            return False
    
    @asynccontextmanager
    async def lock_context(
        self, 
        resource_key: str, 
        ttl_seconds: int = None,
        timeout_seconds: float = 5.0
    ):
        """
        Context manager for automatic lock acquisition and release.
        
        Usage:
            async with lock_manager.lock_context("resource_key") as lock:
                if lock:
                    # Lock acquired, perform protected operation
                    pass
                else:
                    # Lock not acquired, handle appropriately
                    pass
        """
        lock_info = await self.acquire_lock(resource_key, ttl_seconds, timeout_seconds)
        
        try:
            yield lock_info
        finally:
            if lock_info:
                await self.release_lock(lock_info)
    
    async def prevent_cache_stampede(
        self,
        cache_key: str,
        cache_rebuild_func: Callable[[], Awaitable[Any]],
        cache_ttl: int = 300,
        lock_ttl: int = 60,
        timeout_seconds: float = 10.0
    ) -> Any:
        """
        Prevent cache stampede by coordinating cache rebuilds with distributed locking.
        
        This method implements the cache stampede prevention pattern:
        1. Check if data exists in cache
        2. If not, try to acquire rebuild lock
        3. If lock acquired, rebuild cache and return data
        4. If lock not acquired, wait and check cache again
        
        Args:
            cache_key: Cache key to protect
            cache_rebuild_func: Async function to rebuild cache data
            cache_ttl: TTL for cached data
            lock_ttl: TTL for rebuild lock
            timeout_seconds: Maximum time to wait for cache rebuild
            
        Returns:
            Cached or rebuilt data
        """
        start_time = time.time()
        
        # Initialize metrics
        metrics = StampedePreventionMetrics(
            operation_type="cache_stampede_prevention",
            cache_key=cache_key,
            lock_acquired=False,
            lock_wait_time_ms=0.0,
            total_execution_time_ms=0.0
        )
        
        try:
            # First, try to get from cache
            cached_data = await self.cache.get(cache_key)
            if cached_data is not None:
                metrics.total_execution_time_ms = (time.time() - start_time) * 1000
                self.metrics.append(metrics)
                return cached_data
            
            # Cache miss - try to acquire rebuild lock
            lock_start = time.time()
            rebuild_lock_key = f"rebuild:{cache_key}"
            
            async with self.lock_context(rebuild_lock_key, lock_ttl, timeout_seconds) as lock:
                metrics.lock_wait_time_ms = (time.time() - lock_start) * 1000
                
                if lock:
                    # Lock acquired - we are responsible for rebuilding
                    metrics.lock_acquired = True
                    logger.debug(f"Acquired rebuild lock for: {cache_key}")
                    
                    # Double-check cache (another process might have rebuilt it)
                    cached_data = await self.cache.get(cache_key)
                    if cached_data is not None:
                        metrics.total_execution_time_ms = (time.time() - start_time) * 1000
                        self.metrics.append(metrics)
                        return cached_data
                    
                    # Rebuild cache data
                    rebuild_start = time.time()
                    try:
                        new_data = await cache_rebuild_func()
                        metrics.cache_rebuild_time_ms = (time.time() - rebuild_start) * 1000
                        
                        # Store in cache
                        await self.cache.set(cache_key, new_data, ttl=cache_ttl)
                        
                        logger.debug(f"Cache rebuilt for: {cache_key}")
                        metrics.total_execution_time_ms = (time.time() - start_time) * 1000
                        self.metrics.append(metrics)
                        
                        return new_data
                        
                    except Exception as e:
                        logger.error(f"Error rebuilding cache for {cache_key}: {e}")
                        raise
                
                else:
                    # Lock not acquired - another process is rebuilding
                    # Wait and poll cache until data is available or timeout
                    logger.debug(f"Waiting for cache rebuild: {cache_key}")
                    
                    poll_start = time.time()
                    poll_interval = 0.1  # 100ms polling interval
                    max_poll_time = timeout_seconds
                    
                    while (time.time() - poll_start) < max_poll_time:
                        cached_data = await self.cache.get(cache_key)
                        if cached_data is not None:
                            metrics.total_execution_time_ms = (time.time() - start_time) * 1000
                            self.metrics.append(metrics)
                            return cached_data
                        
                        await asyncio.sleep(poll_interval)
                    
                    # Timeout waiting for rebuild - fallback to direct rebuild
                    logger.warning(f"Timeout waiting for cache rebuild: {cache_key}")
                    rebuild_start = time.time()
                    new_data = await cache_rebuild_func()
                    metrics.cache_rebuild_time_ms = (time.time() - rebuild_start) * 1000
                    
                    # Try to cache (best effort)
                    try:
                        await self.cache.set(cache_key, new_data, ttl=cache_ttl)
                    except Exception as e:
                        logger.warning(f"Failed to cache data after timeout: {e}")
                    
                    metrics.total_execution_time_ms = (time.time() - start_time) * 1000
                    self.metrics.append(metrics)
                    
                    return new_data
        
        except Exception as e:
            metrics.total_execution_time_ms = (time.time() - start_time) * 1000
            self.metrics.append(metrics)
            logger.error(f"Error in cache stampede prevention for {cache_key}: {e}")
            raise
    
    async def simulate_concurrent_requests(
        self,
        resource_key: str,
        num_concurrent: int = 10,
        operation_duration: float = 1.0
    ) -> Dict[str, Any]:
        """
        Simulate concurrent requests to demonstrate lock contention and stampede prevention.
        
        Args:
            resource_key: Resource to simulate contention for
            num_concurrent: Number of concurrent requests
            operation_duration: Simulated operation duration in seconds
            
        Returns:
            Dictionary with simulation results and metrics
        """
        start_time = time.time()
        
        async def simulate_request(request_id: int) -> Dict[str, Any]:
            """Simulate a single request."""
            request_start = time.time()
            
            async with self.lock_context(f"sim:{resource_key}", ttl_seconds=10) as lock:
                if lock:
                    # Simulate work while holding lock
                    await asyncio.sleep(operation_duration)
                    
                    return {
                        "request_id": request_id,
                        "lock_acquired": True,
                        "execution_time_ms": (time.time() - request_start) * 1000,
                        "lock_key": lock.lock_key
                    }
                else:
                    return {
                        "request_id": request_id,
                        "lock_acquired": False,
                        "execution_time_ms": (time.time() - request_start) * 1000,
                        "lock_key": None
                    }
        
        # Launch concurrent requests
        tasks = [simulate_request(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_locks = sum(1 for r in results if isinstance(r, dict) and r.get("lock_acquired"))
        failed_locks = num_concurrent - successful_locks
        
        execution_times = [
            r["execution_time_ms"] for r in results 
            if isinstance(r, dict) and "execution_time_ms" in r
        ]
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        total_simulation_time = (time.time() - start_time) * 1000
        
        return {
            "simulation_summary": {
                "resource_key": resource_key,
                "concurrent_requests": num_concurrent,
                "successful_locks": successful_locks,
                "failed_locks": failed_locks,
                "success_rate": successful_locks / num_concurrent,
                "avg_execution_time_ms": avg_execution_time,
                "total_simulation_time_ms": total_simulation_time
            },
            "request_results": [r for r in results if isinstance(r, dict)],
            "errors": [str(r) for r in results if not isinstance(r, dict)]
        }
    
    async def get_lock_status(self, resource_key: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a lock for the given resource.
        
        Args:
            resource_key: Resource identifier
            
        Returns:
            Lock status information or None if no lock exists
        """
        lock_key = key_manager.key_builder.build_key("lock", resource_key)
        
        try:
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Get lock value and TTL
            lock_value = self.cache.client.client.get(lock_key)
            ttl = self.cache.client.client.ttl(lock_key)
            
            if lock_value is None:
                return None
            
            # Parse lock value to get owner info
            lock_value_str = lock_value.decode('utf-8') if isinstance(lock_value, bytes) else str(lock_value) if lock_value else ""
            owner_id = lock_value_str.split(':')[0] if lock_value_str else "unknown"
            
            return {
                "lock_key": lock_key,
                "lock_value": lock_value_str if lock_value else None,
                "owner_id": owner_id,
                "is_owned_by_us": owner_id == self.instance_id,
                "ttl_seconds": ttl if ttl > 0 else 0,
                "exists": True
            }
            
        except Exception as e:
            logger.error(f"Error getting lock status for {resource_key}: {e}")
            return None
    
    def get_active_locks(self) -> List[Dict[str, Any]]:
        """
        Get information about all active locks owned by this instance.
        
        Returns:
            List of active lock information
        """
        return [lock.to_dict() for lock in self.active_locks.values()]
    
    def get_stampede_prevention_metrics(self) -> Dict[str, Any]:
        """
        Get cache stampede prevention metrics and statistics.
        
        Returns:
            Dictionary with metrics and performance data
        """
        if not self.metrics:
            return {"message": "No stampede prevention metrics available"}
        
        total_operations = len(self.metrics)
        successful_locks = sum(1 for m in self.metrics if m.lock_acquired)
        failed_locks = total_operations - successful_locks
        
        avg_lock_wait_time = (
            sum(m.lock_wait_time_ms for m in self.metrics) / total_operations
            if total_operations > 0 else 0.0
        )
        
        avg_rebuild_time = (
            sum(m.cache_rebuild_time_ms for m in self.metrics if m.cache_rebuild_time_ms > 0) /
            sum(1 for m in self.metrics if m.cache_rebuild_time_ms > 0)
        ) if any(m.cache_rebuild_time_ms > 0 for m in self.metrics) else 0.0
        
        return {
            "summary": {
                "total_operations": total_operations,
                "successful_lock_acquisitions": successful_locks,
                "failed_lock_acquisitions": failed_locks,
                "lock_success_rate": successful_locks / total_operations if total_operations > 0 else 0.0,
                "avg_lock_wait_time_ms": avg_lock_wait_time,
                "avg_cache_rebuild_time_ms": avg_rebuild_time,
                "active_locks": len(self.active_locks)
            },
            "recent_operations": [m.to_dict() for m in self.metrics[-10:]],  # Last 10 operations
            "active_locks": self.get_active_locks()
        }
    
    def clear_metrics(self) -> None:
        """Clear collected stampede prevention metrics."""
        self.metrics.clear()
        logger.info("Stampede prevention metrics cleared")
    
    async def cleanup_expired_locks(self) -> int:
        """
        Clean up expired locks from active locks tracking.
        
        Returns:
            Number of expired locks cleaned up
        """
        expired_keys = []
        
        for lock_key, lock_info in self.active_locks.items():
            if lock_info.is_expired:
                expired_keys.append(lock_key)
        
        for key in expired_keys:
            del self.active_locks[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired locks")
        
        return len(expired_keys)