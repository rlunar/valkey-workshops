#!/usr/bin/env python3
"""
Benchmark script to compare performance of city-airport relationship creation.
"""

import time
import sys
import os
from typing import Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from scripts.create_city_airport_relations import CityAirportRelationCreator


def benchmark_performance() -> Dict[str, Any]:
    """Benchmark the optimized city-airport relationship creation"""
    
    print("🚀 City-Airport Relationship Performance Benchmark")
    print("=" * 55)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    creator = CityAirportRelationCreator(db_manager, verbose=True)
    
    results = {}
    
    # Test different configurations
    test_configs = [
        {"name": "Sequential Processing", "use_parallel": False, "batch_size": 500},
        {"name": "Parallel Processing (Small Batches)", "use_parallel": True, "batch_size": 500},
        {"name": "Parallel Processing (Large Batches)", "use_parallel": True, "batch_size": 1000},
    ]
    
    for config in test_configs:
        print(f"\n📊 Testing: {config['name']}")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            creator.create_city_airport_relations(
                max_distance_km=100.0,
                batch_size=config['batch_size'],
                use_parallel=config['use_parallel']
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            results[config['name']] = {
                "execution_time": execution_time,
                "success": True,
                "config": config
            }
            
            print(f"✅ Completed in {execution_time:.2f} seconds")
            
        except Exception as e:
            results[config['name']] = {
                "execution_time": None,
                "success": False,
                "error": str(e),
                "config": config
            }
            print(f"❌ Failed: {e}")
    
    # Print summary
    print("\n📈 Performance Summary")
    print("=" * 30)
    
    successful_runs = {k: v for k, v in results.items() if v['success']}
    
    if successful_runs:
        fastest = min(successful_runs.items(), key=lambda x: x[1]['execution_time'])
        slowest = max(successful_runs.items(), key=lambda x: x[1]['execution_time'])
        
        print(f"🏆 Fastest: {fastest[0]} ({fastest[1]['execution_time']:.2f}s)")
        print(f"🐌 Slowest: {slowest[0]} ({slowest[1]['execution_time']:.2f}s)")
        
        if len(successful_runs) > 1:
            speedup = slowest[1]['execution_time'] / fastest[1]['execution_time']
            print(f"⚡ Speedup: {speedup:.2f}x")
    
    return results


def analyze_performance_bottlenecks():
    """Analyze potential performance bottlenecks and suggest improvements"""
    
    print("\n🔍 Performance Analysis & Recommendations")
    print("=" * 45)
    
    recommendations = [
        {
            "area": "Database Indexing",
            "issue": "Missing spatial indexes on latitude/longitude columns",
            "solution": "Add spatial indexes: CREATE INDEX idx_city_location ON city (latitude, longitude)",
            "impact": "High - Can reduce query time by 10-100x"
        },
        {
            "area": "Memory Usage",
            "issue": "Loading all cities into memory at once",
            "solution": "Implement streaming/chunked city loading for very large datasets",
            "impact": "Medium - Reduces memory usage for datasets >1M cities"
        },
        {
            "area": "Distance Calculations",
            "issue": "Repeated distance calculations for same city pairs",
            "solution": "LRU cache implemented - consider persistent caching for multiple runs",
            "impact": "Medium - 20-50% reduction in computation time"
        },
        {
            "area": "Parallel Processing",
            "issue": "Thread overhead for small datasets",
            "solution": "Automatic fallback to sequential processing for <100 airports",
            "impact": "Low - Prevents overhead on small datasets"
        },
        {
            "area": "Batch Size Optimization",
            "issue": "Fixed batch sizes may not be optimal for all datasets",
            "solution": "Dynamic batch sizing based on available memory and dataset size",
            "impact": "Medium - 10-30% performance improvement"
        }
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['area']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Solution: {rec['solution']}")
        print(f"   Impact: {rec['impact']}")


def main():
    """Main benchmark function"""
    
    # Check if database is available
    try:
        db_manager = DatabaseManager()
        # Quick connection test
        with db_manager.engine.connect() as conn:
            pass
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please ensure your database is running and .env is configured")
        return 1
    
    # Run benchmarks
    results = benchmark_performance()
    
    # Analyze bottlenecks
    analyze_performance_bottlenecks()
    
    print("\n🎯 Key Optimizations Implemented:")
    print("  • Spatial grid indexing (O(1) geographic lookups)")
    print("  • Parallel processing with configurable batch sizes")
    print("  • Distance calculation caching (LRU cache)")
    print("  • Bulk database operations")
    print("  • Early termination for exact matches")
    print("  • Memory-efficient lookup structures")
    
    return 0


if __name__ == "__main__":
    exit(main())