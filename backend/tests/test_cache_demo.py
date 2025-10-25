#!/usr/bin/env python3
"""
Cache system demonstration script.

This script demonstrates the key features of the Valkey cache integration
without requiring a running Valkey instance (uses fallback mode).
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import airport modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from airport.cache import (
    ValkeyConfig,
    CacheManager,
    CacheKeyPrefix,
    TTLPreset,
    key_manager
)


async def demonstrate_cache_system():
    """Demonstrate the cache system features."""
    print("🚀 Valkey Cache System Demonstration")
    print("=" * 50)
    
    # 1. Configuration
    print("\n1. Configuration")
    print("-" * 20)
    config = ValkeyConfig.from_env()
    print(f"Cache config: {config}")
    
    # 2. Cache Manager with Fallback
    print("\n2. Cache Manager (Fallback Mode)")
    print("-" * 35)
    cache = CacheManager(config=config, enable_fallback=True)
    await cache.initialize()
    print("✅ Cache manager initialized with fallback enabled")
    
    # 3. Key Generation
    print("\n3. Key Generation")
    print("-" * 20)
    
    # Flight search key
    search_key = key_manager.flight_search_key(
        "LAX", "JFK", "2024-01-15",
        passengers=2, class_preference="economy"
    )
    print(f"Flight search key: {search_key}")
    
    # Seat reservation keys
    flight_id = "AA123_20240115"
    seat_key = key_manager.seat_reservation_key(flight_id, 12)
    lock_key = key_manager.seat_lock_key(flight_id, 12, "user_456")
    print(f"Seat reservation key: {seat_key}")
    print(f"Seat lock key: {lock_key}")
    
    # Weather key
    weather_key = key_manager.weather_key("US", "Los_Angeles")
    print(f"Weather key: {weather_key}")
    
    # 4. Basic Cache Operations
    print("\n4. Basic Cache Operations")
    print("-" * 30)
    
    # Set some data
    flight_data = {
        "flight_number": "AA123",
        "departure": "2024-01-15T08:00:00",
        "arrival": "2024-01-15T16:30:00",
        "price": 299.99,
        "available_seats": 45
    }
    
    success = await cache.set(search_key, flight_data, ttl=TTLPreset.SEARCH_RESULTS)
    print(f"✅ Set flight data: {success}")
    
    # Get data back
    retrieved = await cache.get(search_key)
    print(f"✅ Retrieved flight data: {retrieved is not None}")
    if retrieved:
        print(f"   Flight: {retrieved['flight_number']} - ${retrieved['price']}")
    
    # Check existence
    exists = await cache.exists(search_key)
    print(f"✅ Key exists: {exists}")
    
    # 5. TTL and Expiration
    print("\n5. TTL Management")
    print("-" * 20)
    
    # Set with different TTL presets
    ttl_examples = [
        ("Near real-time data", TTLPreset.NEAR_REAL_TIME),
        ("Flight status", TTLPreset.FLIGHT_STATUS),
        ("Weather data", TTLPreset.WEATHER_DATA),
        ("Search results", TTLPreset.SEARCH_RESULTS),
    ]
    
    for description, ttl_preset in ttl_examples:
        test_key = f"ttl:example:{ttl_preset}"
        await cache.set(test_key, {"data": description}, ttl=ttl_preset)
        ttl = await cache.get_ttl(test_key)
        print(f"   {description}: {ttl_preset}s TTL (actual: {ttl}s)")
    
    # 6. Error Handling and Fallback
    print("\n6. Error Handling & Fallback")
    print("-" * 35)
    
    # Demonstrate fallback cache
    fallback_key = "fallback:test"
    fallback_data = {"message": "This works even without Valkey!"}
    
    await cache.set(fallback_key, fallback_data, ttl=300)
    fallback_retrieved = await cache.get(fallback_key)
    print(f"✅ Fallback cache works: {fallback_retrieved is not None}")
    
    # 7. Statistics
    print("\n7. Performance Statistics")
    print("-" * 30)
    
    stats = await cache.get_stats()
    print(f"   Total operations: {stats['total_operations']}")
    print(f"   Hit count: {stats['hit_count']}")
    print(f"   Miss count: {stats['miss_count']}")
    print(f"   Hit ratio: {stats['hit_ratio']:.2%}")
    print(f"   Fallback operations: {stats['fallback_operations']}")
    print(f"   Error count: {stats['error_count']}")
    
    # 8. Health Check
    print("\n8. Health Check")
    print("-" * 18)
    
    health = await cache.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Cache available: {health['cache_available']}")
    print(f"   Fallback active: {health.get('fallback_active', False)}")
    
    # 9. Workshop Scenarios
    print("\n9. Workshop Scenarios")
    print("-" * 25)
    
    # Seat reservation scenario
    print("   🪑 Seat Reservation:")
    seat_data = {
        "user_id": "user_456",
        "seat_number": 12,
        "reserved_at": "2024-01-15T10:30:00Z",
        "flight_id": flight_id
    }
    await cache.set(seat_key, seat_data, ttl=TTLPreset.SEAT_RESERVATION)
    await cache.set(lock_key, "locked", ttl=TTLPreset.SEAT_RESERVATION)
    print(f"      Reserved seat 12 for user_456 (60s hold)")
    
    # Weather caching scenario
    print("   🌤️  Weather Caching:")
    weather_data = {
        "temperature": 72,
        "condition": "sunny",
        "humidity": 45,
        "cached_at": "2024-01-15T10:30:00Z"
    }
    await cache.set(weather_key, weather_data, ttl=TTLPreset.WEATHER_DATA)
    print(f"      Cached weather for Los Angeles (15min TTL)")
    
    # Leaderboard scenario
    print("   🏆 Leaderboard:")
    leaderboard_key = key_manager.leaderboard_key("passenger_bookings")
    leaderboard_data = {
        "top_passengers": [
            {"passenger_id": 1, "bookings": 15, "name": "John Doe"},
            {"passenger_id": 2, "bookings": 12, "name": "Jane Smith"},
            {"passenger_id": 3, "bookings": 10, "name": "Bob Wilson"}
        ],
        "last_updated": "2024-01-15T10:30:00Z"
    }
    await cache.set(leaderboard_key, leaderboard_data, ttl=TTLPreset.LEADERBOARD)
    print(f"      Cached passenger leaderboard (10min TTL)")
    
    # 10. Cleanup
    print("\n10. Cleanup")
    print("-" * 15)
    
    await cache.close()
    print("✅ Cache manager closed")
    
    print("\n🎉 Cache system demonstration completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(demonstrate_cache_system())