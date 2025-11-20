"""
Cache-Aside / Lazy Loading Pattern Implementation

Supports multiple database engines (MySQL, MariaDB, PostgreSQL) and
cache engines (Redis, Valkey, Memcached) via environment variables.
"""

import os
import hashlib
import json
from typing import Any, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Load environment variables
load_dotenv()


class CacheAside:
    """Cache-aside pattern implementation with pluggable backends."""
    
    def __init__(self):
        """Initialize database and cache connections from environment variables."""
        self.db_engine = self._create_db_engine()
        self.cache_client = self._create_cache_client()
        self.default_ttl = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
    
    def _create_db_engine(self) -> Engine:
        """Create SQLAlchemy engine based on DB_ENGINE environment variable."""
        db_type = os.getenv("DB_ENGINE", "mysql").lower()
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_user = os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "flughafendb_large")
        
        # Build connection string based on engine type
        if db_type in ["mysql", "mariadb"]:
            connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        elif db_type == "postgresql":
            connection_string = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            raise ValueError(f"Unsupported DB_ENGINE: {db_type}")
        
        return create_engine(connection_string)
    
    def _create_cache_client(self) -> Any:
        """Create cache client based on CACHE_ENGINE environment variable."""
        cache_type = os.getenv("CACHE_ENGINE", "redis").lower()
        cache_host = os.getenv("CACHE_HOST", "localhost")
        cache_port = int(os.getenv("CACHE_PORT", "6379"))
        
        if cache_type in ["redis", "valkey"]:
            try:
                import valkey
            except ImportError:
                import redis as valkey
            return valkey.Redis(
                host=cache_host,
                port=cache_port,
                decode_responses=True
            )
        elif cache_type == "memcached":
            from pymemcache.client import base
            return base.Client((cache_host, cache_port))
        else:
            raise ValueError(f"Unsupported CACHE_ENGINE: {cache_type}")
    
    def _generate_cache_key(self, query: str) -> str:
        """Generate cache key from SQL query using SHA256 hash."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        return f"query:{query_hash}"
    
    def _cache_get(self, key: str) -> Optional[str]:
        """Get value from cache (handles different cache backends)."""
        cache_type = os.getenv("CACHE_ENGINE", "redis").lower()
        
        try:
            if cache_type in ["redis", "valkey"]:
                return self.cache_client.get(key)
            elif cache_type == "memcached":
                value = self.cache_client.get(key)
                return value.decode() if value else None
        except Exception as e:
            print(f"Cache GET error: {e}")
            return None
    
    def _cache_set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache with TTL (handles different cache backends)."""
        cache_type = os.getenv("CACHE_ENGINE", "redis").lower()
        
        try:
            if cache_type in ["redis", "valkey"]:
                self.cache_client.setex(key, ttl, value)
            elif cache_type == "memcached":
                self.cache_client.set(key, value.encode(), expire=ttl)
        except Exception as e:
            print(f"Cache SET error: {e}")
    
    def execute_query(
        self, 
        query: str, 
        ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Tuple[list, str, float]:
        """
        Execute SQL query with cache-aside pattern.
        
        Args:
            query: SQL query string
            ttl: Cache TTL in seconds (uses default if None)
            force_refresh: If True, bypass cache and refresh from DB
        
        Returns:
            Tuple of (results, source, latency_ms)
            - results: List of dictionaries with query results
            - source: "CACHE_HIT" or "CACHE_MISS"
            - latency_ms: Query execution time in milliseconds
        """
        import time
        
        if ttl is None:
            ttl = self.default_ttl
        
        cache_key = self._generate_cache_key(query)
        
        # 1. Try cache first (unless force refresh)
        if not force_refresh:
            start = time.time()
            cached_data = self._cache_get(cache_key)
            latency = (time.time() - start) * 1000
            
            if cached_data:
                results = json.loads(cached_data)
                return results, "CACHE_HIT", latency
        
        # 2. Cache miss - query database
        start = time.time()
        with self.db_engine.connect() as conn:
            result = conn.execute(text(query))
            # Convert rows to list of dicts
            results = [dict(row._mapping) for row in result]
        latency = (time.time() - start) * 1000
        
        # 3. Store in cache
        if results:
            self._cache_set(cache_key, json.dumps(results, default=str), ttl)
        
        return results, "CACHE_MISS", latency
    
    def invalidate_query(self, query: str) -> bool:
        """
        Invalidate cached query result.
        
        Args:
            query: SQL query string to invalidate
        
        Returns:
            True if cache entry was deleted, False otherwise
        """
        cache_key = self._generate_cache_key(query)
        cache_type = os.getenv("CACHE_ENGINE", "redis").lower()
        
        try:
            if cache_type in ["redis", "valkey"]:
                return bool(self.cache_client.delete(cache_key))
            elif cache_type == "memcached":
                return self.cache_client.delete(cache_key)
        except Exception as e:
            print(f"Cache invalidation error: {e}")
            return False
    
    def close(self):
        """Close database and cache connections."""
        self.db_engine.dispose()
        
        cache_type = os.getenv("CACHE_ENGINE", "redis").lower()
        if cache_type in ["redis", "valkey"]:
            self.cache_client.close()
        elif cache_type == "memcached":
            self.cache_client.close()


# Example usage
if __name__ == "__main__":
    # Initialize cache-aside handler
    cache = CacheAside()
    
    # Example query
    query = """
        SELECT 
            airline_id,
            iata,
            airlinename,
            base_airport
        FROM airline
        WHERE airline_id = 1
    """
    
    print("=" * 60)
    print("Cache-Aside Pattern Demo")
    print("=" * 60)
    
    # First execution (cache miss)
    print("\n1. First execution (should be CACHE_MISS):")
    results, source, latency = cache.execute_query(query)
    print(f"   Source: {source}")
    print(f"   Latency: {latency:.2f} ms")
    print(f"   Results: {results}")
    
    # Second execution (cache hit)
    print("\n2. Second execution (should be CACHE_HIT):")
    results, source, latency = cache.execute_query(query)
    print(f"   Source: {source}")
    print(f"   Latency: {latency:.2f} ms")
    print(f"   Results: {results}")
    
    # Force refresh
    print("\n3. Force refresh (bypasses cache):")
    results, source, latency = cache.execute_query(query, force_refresh=True)
    print(f"   Source: {source}")
    print(f"   Latency: {latency:.2f} ms")
    
    # Invalidate cache
    print("\n4. Invalidating cache...")
    invalidated = cache.invalidate_query(query)
    print(f"   Cache invalidated: {invalidated}")
    
    # Query after invalidation
    print("\n5. Query after invalidation (should be CACHE_MISS):")
    results, source, latency = cache.execute_query(query)
    print(f"   Source: {source}")
    print(f"   Latency: {latency:.2f} ms")
    
    # Cleanup
    cache.close()
    print("\n" + "=" * 60)
