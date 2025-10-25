"""
Example usage of the Valkey cache system.

This module demonstrates how to use the cache manager, client,
and utilities for common caching operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from . import (
    ValkeyConfig,
    CacheManager,
    CacheKeyPrefix,
    TTLPreset,
    key_manager,
    get_cache_manager
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_cache_operations():
    """Demonstrate basic cache operations."""
    print("\n=== Basic Cache Operations ===")
    
    # Get cache manager (will use environment configuration)
    cache = await get_cache_manager()
    
    # Basic set/get operations
    key = "example:user:123"
    user_data = {
        "id": 123,
        "name": "John Doe",
        "email": "john@example.com",
        "last_login": datetime.now().isoformat()
    }
    
    # Set with TTL
    success = await cache.set(key, user_data, ttl=TTLPreset.PASSENGER_INFO)
    print(f"Set user data: {success}")
    
    # Get data back
    retrieved = await cache.get(key)
    print(f"Retrieved user data: {retrieved}")
    
    # Check if key exists
    exists = await cache.exists(key)
    print(f"Key exists: {exists}")
    
    # Get TTL
    ttl = await cache.get_ttl(key)
    print(f"Remaining TTL: {ttl} seconds")
    
    # Delete key
    deleted = await cache.delete(key)
    print(f"Deleted key: {deleted}")


async def flight_search_caching():
    """Demonstrate flight search result caching."""
    print("\n=== Flight Search Caching ===")
    
    cache = await get_cache_manager()
    
    # Generate cache key for flight search
    search_key = key_manager.flight_search_key(
        from_airport="LAX",
        to_airport="JFK", 
        departure_date="2024-01-15",
        passengers=2,
        class_preference="economy"
    )
    print(f"Generated search key: {search_key}")
    
    # Simulate expensive flight search results
    search_results = {
        "flights": [
            {
                "flight_number": "AA123",
                "departure": "2024-01-15T08:00:00",
                "arrival": "2024-01-15T16:30:00",
                "price": 299.99
            },
            {
                "flight_number": "DL456", 
                "departure": "2024-01-15T14:00:00",
                "arrival": "2024-01-15T22:30:00",
                "price": 279.99
            }
        ],
        "search_time": datetime.now().isoformat(),
        "total_results": 2
    }
    
    # Cache search results
    await cache.set(search_key, search_results, ttl=TTLPreset.SEARCH_RESULTS)
    print("Cached flight search results")
    
    # Retrieve cached results
    cached_results = await cache.get(search_key)
    print(f"Retrieved {len(cached_results['flights'])} cached flights")


async def seat_reservation_demo():
    """Demonstrate seat reservation caching."""
    print("\n=== Seat Reservation Demo ===")
    
    cache = await get_cache_manager()
    
    flight_id = "AA123_20240115"
    seat_number = 12
    user_id = "user_456"
    
    # Generate keys for seat operations
    seat_map_key = key_manager.seat_map_key(flight_id)
    reservation_key = key_manager.seat_reservation_key(flight_id, seat_number)
    lock_key = key_manager.seat_lock_key(flight_id, seat_number, user_id)
    
    print(f"Seat map key: {seat_map_key}")
    print(f"Reservation key: {reservation_key}")
    print(f"Lock key: {lock_key}")
    
    # Simulate seat map
    seat_map = {
        "flight_id": flight_id,
        "total_seats": 180,
        "available_seats": [1, 2, 3, 12, 13, 14],  # Available seat numbers
        "reserved_seats": {},
        "last_updated": datetime.now().isoformat()
    }
    
    await cache.set(seat_map_key, seat_map, ttl=TTLPreset.FLIGHT_MANIFEST)
    
    # Create seat reservation (1 minute hold)
    reservation_data = {
        "user_id": user_id,
        "seat_number": seat_number,
        "reserved_at": datetime.now().isoformat(),
        "expires_in": TTLPreset.SEAT_RESERVATION
    }
    
    await cache.set(reservation_key, reservation_data, ttl=TTLPreset.SEAT_RESERVATION)
    await cache.set(lock_key, "locked", ttl=TTLPreset.SEAT_RESERVATION)
    
    print(f"Reserved seat {seat_number} for user {user_id}")


async def performance_monitoring():
    """Demonstrate performance monitoring and statistics."""
    print("\n=== Performance Monitoring ===")
    
    cache = await get_cache_manager()
    
    # Perform some operations to generate stats
    for i in range(10):
        key = f"test:key:{i}"
        await cache.set(key, f"value_{i}", ttl=60)
    
    for i in range(15):  # More gets than sets to show hit/miss ratio
        key = f"test:key:{i % 12}"  # Some will miss
        value = await cache.get(key)
    
    # Get statistics
    stats = await cache.get_stats()
    print(f"Cache Statistics:")
    print(f"  Hit Count: {stats['hit_count']}")
    print(f"  Miss Count: {stats['miss_count']}")
    print(f"  Hit Ratio: {stats['hit_ratio']:.2%}")
    print(f"  Total Operations: {stats['total_operations']}")
    print(f"  Average Response Time: {stats['avg_response_time_ms']:.2f}ms")
    print(f"  Error Count: {stats['error_count']}")
    
    # Health check
    health = await cache.health_check()
    print(f"\nHealth Status: {health['status']}")
    print(f"Cache Available: {health['cache_available']}")


async def error_handling_demo():
    """Demonstrate error handling and graceful degradation."""
    print("\n=== Error Handling Demo ===")
    
    # Create cache manager with fallback enabled
    cache = CacheManager(enable_fallback=True)
    await cache.initialize()
    
    # This will work even if Valkey is not available (uses fallback)
    test_key = "fallback:test"
    test_value = {"message": "This works even without Valkey!"}
    
    success = await cache.set(test_key, test_value, ttl=300)
    print(f"Set with fallback: {success}")
    
    retrieved = await cache.get(test_key)
    print(f"Retrieved with fallback: {retrieved}")
    
    # Show fallback cache statistics
    stats = await cache.get_stats()
    print(f"Fallback operations: {stats['fallback_operations']}")
    print(f"Degraded operations: {stats['degraded_operations']}")


async def main():
    """Run all cache examples."""
    print("Valkey Cache System Examples")
    print("=" * 40)
    
    try:
        await basic_cache_operations()
        await flight_search_caching()
        await seat_reservation_demo()
        await performance_monitoring()
        await error_handling_demo()
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        
    finally:
        # Cleanup
        from . import close_global_cache_manager
        await close_global_cache_manager()
        print("\n=== Examples completed ===")


if __name__ == "__main__":
    asyncio.run(main())