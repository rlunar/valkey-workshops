#!/usr/bin/env python3
"""
Leaderboard System Demo Script

This script demonstrates the enhanced leaderboard functionality including:
- Passenger booking leaderboards
- Airport traffic leaderboards  
- Passenger miles leaderboards
- Performance comparison with RDBMS
"""

import asyncio
import time
from airport.services.leaderboard import (
    LeaderboardSystem, 
    AirportTrafficLeaderboard, 
    PassengerMilesLeaderboard,
    MultiLeaderboardManager
)
from airport.cache.client import ValkeyClient
from airport.cache.config import ValkeyConfig


async def demo_passenger_bookings():
    """Demo passenger booking leaderboard."""
    print("\n🎯 PASSENGER BOOKING LEADERBOARD DEMO")
    print("=" * 50)
    
    # Create mock client for demo
    from test_leaderboard_system import MockValkeyClient
    mock_client = MockValkeyClient()
    
    leaderboard = LeaderboardSystem(mock_client, "demo_bookings")
    
    # Add sample passengers
    passengers = [
        ("alice_smith", 15, {"name": "Alice Smith", "firstname": "Alice", "lastname": "Smith"}),
        ("bob_jones", 12, {"name": "Bob Jones", "firstname": "Bob", "lastname": "Jones"}),
        ("charlie_brown", 18, {"name": "Charlie Brown", "firstname": "Charlie", "lastname": "Brown"}),
        ("diana_wilson", 9, {"name": "Diana Wilson", "firstname": "Diana", "lastname": "Wilson"}),
        ("eve_davis", 21, {"name": "Eve Davis", "firstname": "Eve", "lastname": "Davis"}),
    ]
    
    print("Adding passenger bookings...")
    for passenger_id, bookings, info in passengers:
        await leaderboard.update_passenger_score(passenger_id, bookings, info)
        print(f"  ✓ {info['name']}: {bookings} bookings")
    
    # Show top passengers
    print("\n🏆 Top Passengers by Bookings:")
    top_passengers = await leaderboard.get_top_passengers(limit=5)
    for entry in top_passengers:
        print(f"  {entry.rank}. {entry.passenger_name}: {entry.booking_count} bookings")
    
    # Show statistics
    stats = await leaderboard.get_leaderboard_stats()
    if stats:
        print(f"\n📊 Statistics:")
        print(f"  Total passengers: {stats.total_passengers}")
        print(f"  Total bookings: {stats.total_bookings}")
        print(f"  Average bookings per passenger: {stats.average_score:.1f}")


async def demo_airport_traffic():
    """Demo airport traffic leaderboard."""
    print("\n✈️  AIRPORT TRAFFIC LEADERBOARD DEMO")
    print("=" * 50)
    
    from test_leaderboard_system import MockValkeyClient
    mock_client = MockValkeyClient()
    
    airport_lb = AirportTrafficLeaderboard(mock_client, "demo_traffic")
    
    # Add sample airports
    airports = [
        ("LAX", 1200, 1100, {"name": "Los Angeles International", "city": "Los Angeles"}),
        ("JFK", 1000, 950, {"name": "John F. Kennedy International", "city": "New York"}),
        ("ORD", 800, 750, {"name": "O'Hare International", "city": "Chicago"}),
        ("ATL", 1500, 1400, {"name": "Hartsfield-Jackson Atlanta International", "city": "Atlanta"}),
        ("DFW", 900, 850, {"name": "Dallas/Fort Worth International", "city": "Dallas"}),
    ]
    
    print("Adding airport traffic data...")
    for airport_code, inbound, outbound, info in airports:
        await airport_lb.update_airport_traffic(airport_code, inbound, outbound, info)
        total = inbound + outbound
        print(f"  ✓ {airport_code} ({info['name']}): {total:,} passengers ({inbound:,} in, {outbound:,} out)")
    
    # Show top airports
    print("\n🏆 Top Airports by Traffic:")
    top_airports = await airport_lb.get_top_airports_by_traffic(limit=5)
    for entry in top_airports:
        print(f"  {entry.rank}. {entry.airport_code}: {entry.total_passengers:,} passengers")
        print(f"      ({entry.inbound_passengers:,} inbound, {entry.outbound_passengers:,} outbound)")


async def demo_passenger_miles():
    """Demo passenger miles leaderboard."""
    print("\n🌍 PASSENGER MILES LEADERBOARD DEMO")
    print("=" * 50)
    
    from test_leaderboard_system import MockValkeyClient
    mock_client = MockValkeyClient()
    
    miles_lb = PassengerMilesLeaderboard(mock_client, "demo_miles")
    
    # Add sample flight data
    flight_data = [
        ("frequent_flyer_1", [2500, 1800, 3200, 1200, 4500], {"name": "Sarah Johnson"}),
        ("frequent_flyer_2", [5000, 2200, 1500], {"name": "Mike Chen"}),
        ("frequent_flyer_3", [1200, 800, 1500, 2000, 900, 1100], {"name": "Emma Rodriguez"}),
        ("frequent_flyer_4", [8000, 3500], {"name": "David Kim"}),
        ("frequent_flyer_5", [2800, 2100, 1900, 2400], {"name": "Lisa Thompson"}),
    ]
    
    print("Adding flight miles data...")
    for passenger_id, flights, info in flight_data:
        total_miles = 0
        for miles in flights:
            result = await miles_lb.add_flight_miles(passenger_id, miles, info)
            total_miles += miles
        print(f"  ✓ {info['name']}: {total_miles:,} miles across {len(flights)} flights")
    
    # Show top passengers by miles
    print("\n🏆 Top Passengers by Miles:")
    top_passengers = await miles_lb.get_top_passengers_by_miles(limit=5)
    for entry in top_passengers:
        print(f"  {entry.rank}. {entry.passenger_name}: {entry.total_miles:,} miles")
        print(f"      ({entry.total_flights} flights, avg: {entry.average_miles_per_flight:,.0f} miles/flight)")


async def demo_performance_comparison():
    """Demo performance comparison between Valkey and RDBMS."""
    print("\n⚡ PERFORMANCE COMPARISON DEMO")
    print("=" * 50)
    
    from test_leaderboard_system import MockValkeyClient
    mock_client = MockValkeyClient()
    
    manager = MultiLeaderboardManager(mock_client)
    
    print("Simulating mixed workload operations...")
    
    # Simulate some operations
    start_time = time.time()
    
    # Passenger bookings
    for i in range(20):
        await manager.passenger_bookings.increment_passenger_score(
            f"passenger_{i}", 
            1, 
            {"name": f"Passenger {i}"}
        )
    
    # Airport traffic
    airports = ["LAX", "JFK", "ORD", "ATL", "DFW"]
    for i, airport in enumerate(airports):
        await manager.airport_traffic.increment_airport_traffic(
            airport, 
            inbound_increment=50 + i * 10, 
            outbound_increment=45 + i * 8,
            airport_info={"name": f"Airport {airport}"}
        )
    
    # Passenger miles
    for i in range(15):
        await manager.passenger_miles.add_flight_miles(
            f"miles_passenger_{i}", 
            1500 + i * 200,
            {"name": f"Miles Passenger {i}"}
        )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Completed 60 operations in {duration:.3f} seconds")
    print(f"   Performance: {60/duration:.1f} operations/second")
    
    # Get performance report
    report = await manager.get_comprehensive_performance_report()
    
    print(f"\n📊 Performance Analysis:")
    print(f"   Total operations measured: {report.get('total_operations_measured', 0)}")
    
    overall = report.get('overall_performance', {})
    if overall:
        print(f"   Average Valkey time: {overall.get('avg_valkey_time_ms', 0):.2f}ms")
        print(f"   Estimated RDBMS time: {overall.get('avg_estimated_rdbms_time_ms', 0):.2f}ms")
        print(f"   Performance improvement: {overall.get('overall_improvement_factor', 0):.1f}x faster")
    
    print(f"\n💡 Key Benefits of Valkey vs RDBMS:")
    print(f"   • Atomic operations (ZADD, ZINCRBY) vs SQL transactions")
    print(f"   • Fast range queries (ZREVRANGE) vs ORDER BY + LIMIT")
    print(f"   • No table locks or complex joins required")
    print(f"   • Real-time updates without aggregation delays")


async def main():
    """Run all leaderboard demos."""
    print("🚀 VALKEY LEADERBOARD SYSTEM DEMONSTRATION")
    print("=" * 70)
    print("This demo showcases three types of real-time leaderboards:")
    print("1. Passenger Booking Rankings")
    print("2. Airport Traffic Rankings") 
    print("3. Passenger Miles Rankings")
    print("4. Performance Comparison with RDBMS")
    
    try:
        await demo_passenger_bookings()
        await demo_airport_traffic()
        await demo_passenger_miles()
        await demo_performance_comparison()
        
        print(f"\n🎉 DEMO COMPLETE!")
        print(f"=" * 70)
        print(f"The leaderboard system demonstrates how Valkey sorted sets")
        print(f"provide significant performance advantages over traditional")
        print(f"RDBMS approaches for real-time ranking and aggregation tasks.")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())