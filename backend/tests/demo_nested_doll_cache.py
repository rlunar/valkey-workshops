#!/usr/bin/env python3
"""
Nested Doll Cache Demonstration Script

This script demonstrates the key features of the nested doll caching system
including hierarchical caching, selective invalidation, and performance benefits.
"""

import asyncio
import sys
import os
from datetime import date, datetime
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from airport.services.nested_doll_cache import NestedDollCache
from airport.cache.manager import CacheManager


async def demonstrate_nested_doll_cache():
    """Comprehensive demonstration of nested doll cache features."""
    
    print("🎭 Nested Doll Cache System Demonstration")
    print("=" * 60)
    
    # Initialize cache system
    print("\n🔧 Initializing Cache System...")
    cache_manager = CacheManager(client=None, enable_fallback=True)
    await cache_manager.initialize()
    
    nested_doll = NestedDollCache(cache_manager)
    print("✅ Nested doll cache system initialized")
    
    # Demo parameters
    airport_id = "1"
    flight_date = date(2024, 1, 15)
    flight_id = "123"
    
    try:
        # 1. Demonstrate hierarchical caching
        print("\n📊 DEMO 1: Hierarchical Cache Structure")
        print("-" * 45)
        
        print("Creating nested cache hierarchy...")
        airport_data = await nested_doll.cache_airport_daily_flights(airport_id, flight_date)
        
        print(f"✅ Cached airport daily flights for {airport_data['airport']['name']}")
        print(f"   📅 Date: {airport_data['flight_date']}")
        print(f"   ✈️  Departing flights: {len(airport_data['departing_flights'])}")
        print(f"   🛬 Arriving flights: {len(airport_data['arriving_flights'])}")
        
        # Show dependency graph
        graph_info = await nested_doll.get_dependency_graph_info()
        print(f"   🔗 Total dependencies: {graph_info['total_dependencies']}")
        print(f"   📊 Cache fragments: {graph_info['total_cache_keys']}")
        
        # 2. Demonstrate cache hierarchy visualization
        print("\n🌳 DEMO 2: Cache Hierarchy Visualization")
        print("-" * 45)
        
        visualization = await nested_doll.visualize_cache_hierarchy(airport_id, flight_date)
        print(visualization)
        
        # 3. Demonstrate selective invalidation
        print("\n🎯 DEMO 3: Selective Invalidation")
        print("-" * 35)
        
        print("Simulating flight status change (delay)...")
        status_simulation = await nested_doll.simulate_flight_status_change(
            flight_id, "delayed", delay_minutes=30, gate="A12"
        )
        
        print(f"✅ Status change simulation completed:")
        print(f"   ⏱️  Processing time: {status_simulation['performance']['total_time_ms']:.2f}ms")
        print(f"   🔄 Keys invalidated: {status_simulation['performance']['keys_invalidated']}")
        print(f"   💾 Schedule preserved: {status_simulation['after_state']['schedule_preserved']}")
        
        # 4. Demonstrate cascade invalidation
        print("\n🌊 DEMO 4: Cascade Invalidation")
        print("-" * 32)
        
        print("Simulating flight schedule change...")
        schedule_simulation = await nested_doll.simulate_flight_schedule_change(
            flight_id,
            "2024-01-15T11:00:00",
            "2024-01-15T13:00:00",
            "B15"
        )
        
        print(f"✅ Schedule change simulation completed:")
        print(f"   ⏱️  Processing time: {schedule_simulation['performance']['total_time_ms']:.2f}ms")
        print(f"   🔄 Keys invalidated: {schedule_simulation['performance']['keys_invalidated']}")
        print(f"   🌊 Cascade invalidation: {schedule_simulation['performance']['cascade_invalidation']}")
        
        # 5. Demonstrate performance comparison
        print("\n⚡ DEMO 5: Performance Comparison")
        print("-" * 33)
        
        print("Comparing nested vs flat caching strategies...")
        comparison = await nested_doll.compare_with_flat_caching(airport_id, flight_date)
        
        nested = comparison["nested_caching"]
        flat = comparison["flat_caching"]
        perf_diff = comparison["performance_difference"]
        
        print(f"✅ Performance comparison completed:")
        print(f"   🏗️  Nested caching: {nested['response_time_ms']:.2f}ms ({nested['fragments_count']} fragments)")
        print(f"   📄 Flat caching: {flat['response_time_ms']:.2f}ms ({flat['fragments_count']} fragment)")
        print(f"   🏆 Faster approach: {'Nested' if perf_diff['nested_faster'] else 'Flat'}")
        print(f"   📈 Cache efficiency (nested): {perf_diff['cache_efficiency_nested']:.1%}")
        print(f"   📈 Cache efficiency (flat): {perf_diff['cache_efficiency_flat']:.1%}")
        
        # 6. Demonstrate passenger manifest caching
        print("\n👥 DEMO 6: Passenger Manifest Caching")
        print("-" * 37)
        
        print("Caching flight passenger manifest...")
        manifest_key = await nested_doll.cache_flight_manifest(flight_id)
        
        manifest_data = await cache_manager.get(manifest_key)
        if manifest_data:
            print(f"✅ Flight manifest cached:")
            print(f"   ✈️  Flight: {manifest_data['flight_number']}")
            print(f"   👥 Total passengers: {manifest_data['total_passengers']}")
            print(f"   ✅ Checked in: {manifest_data['checked_in_count']}")
            print(f"   💺 Seat assignments: {len(manifest_data['seat_map'])} seats")
        
        # 7. Demonstrate complex dependencies
        print("\n🕸️  DEMO 7: Complex Dependencies")
        print("-" * 32)
        
        print("Demonstrating cross-cutting dependencies...")
        complex_demo = await nested_doll.demonstrate_complex_dependencies(flight_id)
        
        scenarios = complex_demo["scenarios"]
        analysis = complex_demo["dependency_analysis"]
        
        print(f"✅ Complex dependencies demonstration:")
        print(f"   🔄 Passenger detail change: {len(scenarios['passenger_detail_change']['invalidated_keys'])} keys")
        print(f"   📋 Manifest change: {len(scenarios['manifest_change']['invalidated_keys'])} keys")
        print(f"   🎫 Booking change: {len(scenarios['booking_change']['invalidated_keys'])} keys")
        print(f"   🎯 Selective invalidation: {analysis['cache_efficiency']['selective_invalidation']}")
        
        # 8. Demonstrate cache assembly
        print("\n🔧 DEMO 8: Cache Assembly Process")
        print("-" * 33)
        
        print("Demonstrating cache fragment assembly...")
        assembly_demo = await nested_doll.demonstrate_cache_assembly(airport_id, flight_date)
        
        timing = assembly_demo["timing"]
        cache_ops = assembly_demo["cache_operations"]
        
        print(f"✅ Cache assembly demonstration:")
        print(f"   ⏱️  Total time: {timing['total_time_ms']:.2f}ms")
        print(f"   🎯 Cache hits: {cache_ops['hits']}")
        print(f"   ❌ Cache misses: {cache_ops['misses']}")
        print(f"   🧩 Fragments resolved: {cache_ops['fragments_resolved']}")
        print(f"   📊 Hit ratio: {cache_ops['hits'] / max(1, cache_ops['hits'] + cache_ops['misses']):.1%}")
        
        # Final summary
        print("\n🎉 DEMONSTRATION SUMMARY")
        print("=" * 30)
        print("✅ Hierarchical cache structure created and visualized")
        print("✅ Selective invalidation preserves unaffected data")
        print("✅ Cascade invalidation handles dependent data changes")
        print("✅ Performance benefits demonstrated vs flat caching")
        print("✅ Passenger manifest with cross-cutting dependencies")
        print("✅ Complex dependency patterns handled correctly")
        print("✅ Cache assembly process optimized for efficiency")
        
        print(f"\n📊 Final Cache Statistics:")
        final_graph = await nested_doll.get_dependency_graph_info()
        print(f"   🔗 Total dependencies: {final_graph['total_dependencies']}")
        print(f"   📊 Cache keys: {final_graph['total_cache_keys']}")
        print(f"   🌳 Root keys: {len(final_graph['root_keys'])}")
        print(f"   🍃 Leaf keys: {len(final_graph['leaf_keys'])}")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await cache_manager.close()
        print("\n🧹 Cache system cleaned up")


async def run_quick_demo():
    """Run a quick demonstration of key features."""
    
    print("🚀 Quick Nested Doll Cache Demo")
    print("=" * 40)
    
    # Initialize
    cache_manager = CacheManager(client=None, enable_fallback=True)
    await cache_manager.initialize()
    nested_doll = NestedDollCache(cache_manager)
    
    try:
        # Quick hierarchy demo
        print("\n1️⃣  Creating cache hierarchy...")
        airport_data = await nested_doll.cache_airport_daily_flights("1", date(2024, 1, 15))
        print(f"   ✅ Cached {airport_data['airport']['name']} with {len(airport_data['departing_flights']) + len(airport_data['arriving_flights'])} flights")
        
        # Quick invalidation demo
        print("\n2️⃣  Testing selective invalidation...")
        invalidated = await nested_doll.invalidate_flight_status("123", "demo_delay")
        print(f"   ✅ Selectively invalidated {len(invalidated)} cache keys")
        
        # Quick performance demo
        print("\n3️⃣  Comparing performance...")
        comparison = await nested_doll.compare_with_flat_caching("1", date(2024, 1, 15))
        nested_time = comparison["nested_caching"]["response_time_ms"]
        flat_time = comparison["flat_caching"]["response_time_ms"]
        print(f"   ✅ Nested: {nested_time:.2f}ms, Flat: {flat_time:.2f}ms")
        
        print("\n🎉 Quick demo completed successfully!")
        
    finally:
        await cache_manager.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nested Doll Cache Demonstration")
    parser.add_argument("--quick", action="store_true", help="Run quick demo instead of full demonstration")
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(run_quick_demo())
    else:
        asyncio.run(demonstrate_nested_doll_cache())


if __name__ == "__main__":
    main()