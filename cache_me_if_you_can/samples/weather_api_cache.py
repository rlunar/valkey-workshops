"""
Weather API Cache Demo - Cache-Aside Pattern with Lazy Loading

This demo showcases the cache-aside pattern with blocking lazy loading for weather data.
It compares performance before and after caching with configurable TTL (15, 30, or 60 minutes).
"""

import sys
import time
import random
import json
import os
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.weather_service import WeatherService

# Load environment variables
load_dotenv()


class SimpleCache:
    """Simple Valkey/Redis cache with TTL support for demo purposes."""
    
    def __init__(self, default_ttl: int = 900):
        """
        Initialize Valkey cache connection.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 900 = 15 minutes)
        """
        import redis
        
        self.default_ttl = default_ttl
        cache_host = os.getenv("CACHE_HOST", "localhost")
        cache_port = int(os.getenv("CACHE_PORT", "6379"))
        
        self.client = redis.Redis(
            host=cache_host,
            port=cache_port,
            decode_responses=True
        )
        
        # Test connection
        try:
            self.client.ping()
            print(f"✓ Connected to Valkey at {cache_host}:{cache_port}")
        except redis.ConnectionError as e:
            print(f"✗ Failed to connect to Valkey at {cache_host}:{cache_port}")
            raise e
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache GET error for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            serialized_value = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized_value)
        except Exception as e:
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
            print(f"Lock RELEASE error for key '{key}': {e}")
    
    def clear(self) -> None:
        """Clear all cache entries (use with caution in production!)."""
        try:
            self.client.flushdb()
        except Exception as e:
            print(f"Cache CLEAR error: {e}")
    
    def keys(self, pattern: str = "*") -> list:
        """Get all keys matching pattern."""
        try:
            return self.client.keys(pattern)
        except Exception as e:
            print(f"Cache KEYS error: {e}")
            return []
    
    def close(self) -> None:
        """Close Valkey connection."""
        try:
            self.client.close()
        except Exception as e:
            print(f"Cache CLOSE error: {e}")


def format_time(seconds: float) -> str:
    """Format time in a human-readable way."""
    if seconds < 1:
        return f"{seconds * 1000:.3f}ms"
    return f"{seconds:.3f}s"


def get_random_cities(count: int = 10) -> list:
    """Get random cities from the weather service."""
    all_cities = WeatherService.get_all_cities()
    return random.sample(all_cities, min(count, len(all_cities)))


def fetch_weather_without_cache(cities: list) -> tuple:
    """Fetch weather data without caching."""
    print("\n" + "=" * 70)
    print("FETCHING WITHOUT CACHE (Direct API Calls)")
    print("=" * 70)
    
    results = []
    start_time = time.time()
    
    for i, city in enumerate(cities, 1):
        city_start = time.time()
        weather = WeatherService.get_weather(city['country'], city['zip'])
        city_elapsed = time.time() - city_start
        
        results.append(weather)
        print(f"{i:2d}. {city['name']:20s} ({city['country']}) - {format_time(city_elapsed)}")
    
    total_time = time.time() - start_time
    print(f"\nTotal time: {format_time(total_time)}")
    
    return results, total_time


def fetch_weather_with_cache(cities: list, cache: SimpleCache, run_number: int = 1) -> tuple:
    """Fetch weather data with caching and distributed locking."""
    print("\n" + "=" * 70)
    print(f"FETCHING WITH CACHE (Run #{run_number})")
    print("=" * 70)
    
    results = []
    cache_hits = 0
    cache_misses = 0
    lock_waits = 0
    start_time = time.time()
    
    for i, city in enumerate(cities, 1):
        city_start = time.time()
        cache_key = f"weather:{city['country'].lower()}:{city['zip']}"
        
        # Try to get from cache first
        cached_data = cache.get(cache_key)
        
        if cached_data:
            weather = cached_data
            cache_hits += 1
            status = "CACHE HIT"
        else:
            # Cache miss - try to acquire lock to prevent stampede
            lock_acquired = cache.acquire_lock(cache_key, timeout=10)
            
            if lock_acquired:
                try:
                    # Double-check cache after acquiring lock (another thread might have populated it)
                    cached_data = cache.get(cache_key)
                    if cached_data:
                        weather = cached_data
                        cache_hits += 1
                        status = "CACHE HIT (after lock)"
                    else:
                        # Fetch from API and store in cache
                        weather = WeatherService.get_weather(city['country'], city['zip'])
                        cache.set(cache_key, weather)
                        cache_misses += 1
                        status = "CACHE MISS (populated)"
                finally:
                    # Always release the lock
                    cache.release_lock(cache_key)
            else:
                # Could not acquire lock, wait and retry getting from cache
                lock_waits += 1
                status = "LOCK WAIT"
                max_retries = 20
                retry_delay = 0.5
                
                for retry in range(max_retries):
                    time.sleep(retry_delay)
                    cached_data = cache.get(cache_key)
                    if cached_data:
                        weather = cached_data
                        cache_hits += 1
                        status = f"CACHE HIT (waited {(retry + 1) * retry_delay:.1f}s)"
                        break
                else:
                    # Timeout waiting for lock, fetch anyway
                    weather = WeatherService.get_weather(city['country'], city['zip'])
                    cache.set(cache_key, weather)
                    cache_misses += 1
                    status = "CACHE MISS (timeout)"
        
        city_elapsed = time.time() - city_start
        results.append(weather)
        
        print(f"{i:2d}. {city['name']:20s} ({city['country']}) - {format_time(city_elapsed):>6s} [{status}]")
    
    total_time = time.time() - start_time
    print(f"\nCache Statistics:")
    print(f"  Hits:   {cache_hits}")
    print(f"  Misses: {cache_misses}")
    if lock_waits > 0:
        print(f"  Lock Waits: {lock_waits}")
    print(f"  Hit Rate: {(cache_hits / len(cities) * 100):.1f}%")
    print(f"\nTotal time: {format_time(total_time)}")
    
    return results, total_time, cache_hits, cache_misses


def run_demo(ttl_minutes: int = 15, num_cities: int = 10):
    """
    Run the weather API cache demo.
    
    Args:
        ttl_minutes: Cache TTL in minutes (15, 30, or 60)
        num_cities: Number of random cities to test (default: 10)
    """
    print("\n" + "=" * 70)
    print("WEATHER API CACHE DEMO - Cache-Aside Pattern")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  Cache TTL: {ttl_minutes} minutes")
    print(f"  Number of cities: {num_cities}")
    print(f"  Cache key format: weather:<country>:<zip>")
    
    # Initialize cache with specified TTL
    cache = SimpleCache(default_ttl=ttl_minutes * 60)
    
    # Select random cities
    cities = get_random_cities(num_cities)
    
    print(f"\nSelected cities:")
    for i, city in enumerate(cities, 1):
        print(f"  {i:2d}. {city['name']} ({city['country']}) - {city['zip']}")
    
    # Phase 1: Fetch without cache
    _, time_without_cache = fetch_weather_without_cache(cities)
    
    # Phase 2: First fetch with cache (all misses)
    _, time_first_cache, _, _ = fetch_weather_with_cache(cities, cache, run_number=1)
    
    # Phase 3: Second fetch with cache (all hits)
    print("\n⏳ Waiting 1 second before second fetch...")
    time.sleep(1)
    _, time_second_cache, hits, misses = fetch_weather_with_cache(cities, cache, run_number=2)
    
    # Summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"Without cache:        {format_time(time_without_cache):>8s}")
    print(f"With cache (1st run): {format_time(time_first_cache):>8s} (populating cache)")
    print(f"With cache (2nd run): {format_time(time_second_cache):>8s} (using cache)")
    
    speedup = time_without_cache / time_second_cache if time_second_cache > 0 else 0
    time_saved = time_without_cache - time_second_cache
    
    print(f"\nCache Benefits:")
    print(f"  Time saved: {format_time(time_saved)}")
    print(f"  Speedup: {speedup:.1f}x faster")
    print(f"  Efficiency: {(time_saved / time_without_cache * 100):.1f}% reduction in latency")
    
    # Show cache contents
    cache_keys = cache.keys("weather:*")
    print(f"\n📦 Cache contains {len(cache_keys)} weather entries")
    print(f"   TTL: {ttl_minutes} minutes ({ttl_minutes * 60} seconds)")
    if cache_keys:
        print(f"   Sample keys: {cache_keys[:3]}")
    
    # Cleanup
    cache.close()
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Parse command line arguments
    ttl = 15  # default TTL
    num_cities = 10  # default number of cities
    
    if len(sys.argv) > 1:
        try:
            ttl = int(sys.argv[1])
            if ttl not in [15, 30, 60]:
                print(f"Warning: TTL {ttl} is not standard. Using anyway.")
        except ValueError:
            print(f"Invalid TTL value. Using default: {ttl} minutes")
    
    if len(sys.argv) > 2:
        try:
            num_cities = int(sys.argv[2])
            if num_cities < 1 or num_cities > 95:
                print(f"Number of cities must be between 1 and 95. Using default: 10")
                num_cities = 10
        except ValueError:
            print(f"Invalid number of cities. Using default: {num_cities}")
    
    # Run the demo
    run_demo(ttl_minutes=ttl, num_cities=num_cities)
    
    print("\n💡 Usage: python weather_api_cache.py [ttl_minutes] [num_cities]")
    print("   Example: python weather_api_cache.py 30 15")
    print("   TTL options: 15, 30, or 60 minutes")
    print("   Cities: 1-95 (default: 10)")
