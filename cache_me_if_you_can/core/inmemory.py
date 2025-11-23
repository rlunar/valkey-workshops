"""
In-Memory Cache Connection Manager

Centralized connection management for Valkey/Redis/Memcached cache engines.
Supports multiple cache backends via environment variables.
"""

import os
from typing import Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class InMemoryCache:
    """Factory and wrapper for in-memory cache connections."""
    
    def __init__(
        self,
        cache_type: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        decode_responses: bool = True
    ):
        """
        Initialize cache client based on environment variables or parameters.
        
        Args:
            cache_type: Cache engine type ('redis', 'valkey', 'memcached'). 
                       Defaults to CACHE_ENGINE env var or 'redis'
            host: Cache host. Defaults to CACHE_HOST env var or 'localhost'
            port: Cache port. Defaults to CACHE_PORT env var or 6379
            decode_responses: Whether to decode responses (Redis/Valkey only)
        """
        self.cache_type = (cache_type or os.getenv("CACHE_ENGINE", "redis")).lower()
        self.host = host or os.getenv("CACHE_HOST", "localhost")
        self.port = port or int(os.getenv("CACHE_PORT", "6379"))
        self.decode_responses = decode_responses
        
        self.client = self._create_client()
    
    def _create_client(self) -> Any:
        """Create cache client based on cache type."""
        if self.cache_type in ["redis", "valkey"]:
            try:
                import valkey
            except ImportError:
                import redis as valkey
            
            return valkey.Redis(
                host=self.host,
                port=self.port,
                decode_responses=self.decode_responses
            )
        
        elif self.cache_type == "memcached":
            from pymemcache.client import base
            return base.Client((self.host, self.port))
        
        else:
            raise ValueError(f"Unsupported CACHE_ENGINE: {self.cache_type}")
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value from cache (handles different cache backends).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            if self.cache_type in ["redis", "valkey"]:
                return self.client.get(key)
            elif self.cache_type == "memcached":
                value = self.client.get(key)
                return value.decode() if value else None
        except Exception as e:
            print(f"Cache GET error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        """
        try:
            if self.cache_type in ["redis", "valkey"]:
                if ttl:
                    self.client.setex(key, ttl, value)
                else:
                    self.client.set(key, value)
            elif self.cache_type == "memcached":
                self.client.set(key, value.encode(), expire=ttl or 0)
        except Exception as e:
            print(f"Cache SET error: {e}")
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            if self.cache_type in ["redis", "valkey"]:
                return bool(self.client.delete(key))
            elif self.cache_type == "memcached":
                return self.client.delete(key)
        except Exception as e:
            print(f"Cache DELETE error: {e}")
            return False
    
    def flush_all(self) -> None:
        """Flush all keys from cache."""
        try:
            if self.cache_type in ["redis", "valkey"]:
                self.client.flushall()
            elif self.cache_type == "memcached":
                self.client.flush_all()
        except Exception as e:
            print(f"Cache FLUSH error: {e}")
    
    def close(self) -> None:
        """Close cache connection."""
        try:
            if self.cache_type in ["redis", "valkey"]:
                self.client.close()
            elif self.cache_type == "memcached":
                self.client.close()
        except Exception as e:
            print(f"Cache CLOSE error: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def get_cache_client(
    cache_type: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None
) -> InMemoryCache:
    """
    Factory function to create cache client.
    
    Args:
        cache_type: Cache engine type. Defaults to env var
        host: Cache host. Defaults to env var
        port: Cache port. Defaults to env var
        
    Returns:
        InMemoryCache instance
    """
    return InMemoryCache(cache_type=cache_type, host=host, port=port)


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("In-Memory Cache Connection Test")
    print("=" * 60)
    
    # Test with context manager
    with get_cache_client() as cache:
        print(f"\nCache Type: {cache.cache_type}")
        print(f"Host: {cache.host}:{cache.port}")
        
        # Test operations
        print("\n1. Setting key 'test' = 'hello'")
        cache.set("test", "hello", ttl=60)
        
        print("2. Getting key 'test'")
        value = cache.get("test")
        print(f"   Value: {value}")
        
        print("3. Deleting key 'test'")
        deleted = cache.delete("test")
        print(f"   Deleted: {deleted}")
        
        print("4. Getting deleted key")
        value = cache.get("test")
        print(f"   Value: {value}")
    
    print("\n" + "=" * 60)
