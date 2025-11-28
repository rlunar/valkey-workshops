"""
Unit tests for stampede prevention demo.

Tests the core functionality of distributed locking and stampede prevention.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from daos.weather_api_cache import WeatherAPICache


def test_lock_acquisition():
    """Test that lock can be acquired and released."""
    cache = WeatherAPICache(verbose=False)
    
    # Test lock acquisition
    key = "test:lock:key"
    assert cache.acquire_lock(key, timeout=5), "Should acquire lock on first attempt"
    
    # Test that second acquisition fails
    assert not cache.acquire_lock(key, timeout=5), "Should not acquire lock when already held"
    
    # Release lock
    cache.release_lock(key)
    
    # Test that lock can be acquired again
    assert cache.acquire_lock(key, timeout=5), "Should acquire lock after release"
    cache.release_lock(key)
    
    cache.close()
    print("✓ Lock acquisition test passed")


def test_cache_operations():
    """Test basic cache operations."""
    cache = WeatherAPICache(verbose=False)
    
    # Test set and get
    key = "test:weather:us:12345"
    data = {"temp": 72.5, "condition": "sunny"}
    
    cache.set(key, data, ttl=60)
    retrieved = cache.get(key)
    
    assert retrieved is not None, "Should retrieve cached data"
    assert retrieved["temp"] == 72.5, "Should retrieve correct temperature"
    assert retrieved["condition"] == "sunny", "Should retrieve correct condition"
    
    # Test delete
    cache.delete(key)
    assert cache.get(key) is None, "Should return None after delete"
    
    cache.close()
    print("✓ Cache operations test passed")


def test_double_check_pattern():
    """Test the double-check pattern after lock acquisition."""
    cache = WeatherAPICache(verbose=False)
    
    key = "test:weather:us:54321"
    data = {"temp": 68.0, "condition": "cloudy"}
    
    # Simulate: Thread 1 acquires lock
    assert cache.acquire_lock(key, timeout=5), "Thread 1 should acquire lock"
    
    # Thread 1 populates cache
    cache.set(key, data, ttl=60)
    
    # Thread 1 releases lock
    cache.release_lock(key)
    
    # Simulate: Thread 2 tries to acquire lock but finds data already cached
    cached_data = cache.get(key)
    assert cached_data is not None, "Thread 2 should find cached data"
    assert cached_data["temp"] == 68.0, "Should retrieve correct data"
    
    # Cleanup
    cache.delete(key)
    cache.close()
    print("✓ Double-check pattern test passed")


if __name__ == "__main__":
    print("Running stampede prevention tests...")
    print()
    
    try:
        test_lock_acquisition()
        test_cache_operations()
        test_double_check_pattern()
        
        print()
        print("=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        
    except AssertionError as e:
        print()
        print("=" * 50)
        print(f"❌ Test failed: {e}")
        print("=" * 50)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ Error: {e}")
        print("=" * 50)
        sys.exit(1)
