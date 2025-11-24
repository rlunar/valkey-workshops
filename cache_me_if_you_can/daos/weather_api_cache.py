"""
Weather API Cache - Cache-Aside Pattern with Distributed Locking

This module provides a cache implementation specifically designed for weather API data,
featuring distributed locking to prevent cache stampede and TTL-based expiration.
"""

import sys
import json
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_cache_client


class WeatherAPICache:
    """Weather API cache with TTL support and distributed locking."""
    
    def __init__(self, default_ttl: int = 900, verbose: bool = False):
        """
        Initialize Valkey/Redis cache connection.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 900 = 15 minutes)
            verbose: Enable verbose logging (default: False)
        """
        self.default_ttl = default_ttl
        self.verbose = verbose
        self.cache = get_cache_client()
        self.client = self.cache.client  # For backward compatibility with ping()
        
        # Test connection
        try:
            self.client.ping()
            if self.verbose:
                print(f"✓ Connected to Valkey at {self.cache.host}:{self.cache.port}")
        except Exception as e:
            print(f"✗ Failed to connect to Valkey at {self.cache.host}:{self.cache.port}")
            raise e
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        try:
            value = self.cache.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            if self.verbose:
                print(f"Cache GET error for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be serialized to JSON)
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            serialized_value = json.dumps(value, default=str)
            self.cache.set(key, serialized_value, ttl)
        except Exception as e:
            if self.verbose:
                print(f"Cache SET error for key '{key}': {e}")
    
    def acquire_lock(self, key: str, timeout: int = 10) -> bool:
        """
        Acquire a distributed lock for a key to prevent cache stampede.
        
        Args:
            key: The cache key to lock
            timeout: Lock timeout in seconds (default: 10)
        
        Returns:
            True if lock was acquired, False otherwise
        """
        lock_key = f"lock:{key}"
        try:
            # SET NX (set if not exists) with expiration
            return self.client.set(lock_key, "1", nx=True, ex=timeout)
        except Exception as e:
            if self.verbose:
                print(f"Lock ACQUIRE error for key '{key}': {e}")
            return False
    
    def release_lock(self, key: str) -> None:
        """
        Release a distributed lock for a key.
        
        Args:
            key: The cache key to unlock
        """
        lock_key = f"lock:{key}"
        try:
            self.client.delete(lock_key)
        except Exception as e:
            if self.verbose:
                print(f"Lock RELEASE error for key '{key}': {e}")
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.
        
        Args:
            key: Cache key to delete
        
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            return self.cache.delete(key)
        except Exception as e:
            if self.verbose:
                print(f"Cache DELETE error for key '{key}': {e}")
            return False
    
    def clear(self) -> None:
        """Clear all cache entries (use with caution in production!)."""
        try:
            self.client.flushdb()
            if self.verbose:
                print("Cache cleared successfully")
        except Exception as e:
            print(f"Cache CLEAR error: {e}")
    
    def keys(self, pattern: str = "*") -> list:
        """
        Get all keys matching pattern.
        
        Args:
            pattern: Key pattern (default: "*" for all keys)
        
        Returns:
            List of matching keys
        """
        try:
            return self.client.keys(pattern)
        except Exception as e:
            if self.verbose:
                print(f"Cache KEYS error: {e}")
            return []
    
    def close(self) -> None:
        """Close Valkey/Redis connection."""
        try:
            self.cache.close()
        except Exception as e:
            if self.verbose:
                print(f"Cache CLOSE error: {e}")


# Example usage
if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("Weather API Cache Demo")
    print("=" * 60)
    
    # Initialize cache with 15-minute TTL
    cache = WeatherAPICache(default_ttl=900, verbose=True)
    
    # Example weather data
    weather_data = {
        "coord": {"lon": -122.08, "lat": 37.39},
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
        "main": {"temp": 72.5, "feels_like": 70.2, "humidity": 45},
        "name": "Mountain View"
    }
    
    cache_key = "weather:us:94043"
    
    # Test 1: Set and get
    print(f"\n1. Setting cache key: {cache_key}")
    cache.set(cache_key, weather_data)
    
    print(f"\n2. Getting cache key: {cache_key}")
    cached_data = cache.get(cache_key)
    print(f"   Retrieved: {cached_data}")
    
    # Test 2: Distributed locking
    print(f"\n3. Testing distributed lock for: {cache_key}")
    lock_acquired = cache.acquire_lock(cache_key, timeout=5)
    print(f"   Lock acquired: {lock_acquired}")
    
    if lock_acquired:
        print("   Simulating work while holding lock...")
        time.sleep(1)
        cache.release_lock(cache_key)
        print("   Lock released")
    
    # Test 3: List keys
    print(f"\n4. Listing all weather keys:")
    weather_keys = cache.keys("weather:*")
    print(f"   Found {len(weather_keys)} keys: {weather_keys}")
    
    # Test 4: Delete key
    print(f"\n5. Deleting cache key: {cache_key}")
    deleted = cache.delete(cache_key)
    print(f"   Deleted: {deleted}")
    
    # Verify deletion
    print(f"\n6. Verifying deletion:")
    cached_data = cache.get(cache_key)
    print(f"   Retrieved: {cached_data} (should be None)")
    
    # Cleanup
    cache.close()
    print("\n" + "=" * 60)
