#!/usr/bin/env python3
"""
TTL Optimizer demonstration script.

This script demonstrates the TTL distribution optimizer functionality
including jittered expiration, clustering prevention, and performance
impact analysis.
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock

from airport.services.ttl_optimizer import TTLOptimizer, create_ttl_optimizer


async def demo_ttl_optimizer():
    """Demonstrate TTL optimizer functionality."""
    print("🚀 TTL Distribution Optimizer Demo")
    print("=" * 50)
    
    # Create mock Valkey client for demonstration
    mock_client = Mock()
    mock_client.ensure_connection = AsyncMock()
    mock_client.client = Mock()
    mock_client.client.psetex = Mock(return_value=True)
    mock_client.client.delete = AsyncMock(return_value=1)
    
    # Create TTL optimizer
    optimizer = TTLOptimizer(
        valkey_client=mock_client,
        base_ttl_ms=5000,  # 5 seconds base
        jitter_range_ms=1000,  # ±1 second jitter
        enable_clustering_prevention=True
    )
    
    print("\n📊 1. Basic TTL Calculation with Jitter")
    print("-" * 40)
    
    # Demonstrate basic TTL calculation
    base_ttl = 5  # 5 seconds
    ttl_values = []
    
    for i in range(10):
        ttl_ms = optimizer.calculate_distributed_ttl(base_ttl)
        ttl_values.append(ttl_ms)
        jitter_ms = ttl_ms - (base_ttl * 1000)
        print(f"Key {i+1:2d}: {ttl_ms:5d}ms (jitter: {jitter_ms:+4d}ms)")
    
    print(f"\nTTL Range: {min(ttl_values)}ms - {max(ttl_values)}ms")
    print(f"Variation: {max(ttl_values) - min(ttl_values)}ms")
    
    print("\n🎯 2. Cache Operations with Distributed TTL")
    print("-" * 40)
    
    # Demonstrate cache operations
    test_data = [
        ("flight:search:LAX-JFK", {"route": "LAX-JFK", "results": 15}),
        ("weather:api:NYC", {"temp": 22, "condition": "sunny"}),
        ("user:session:12345", {"user_id": 12345, "preferences": {}}),
    ]
    
    for key, value in test_data:
        success = await optimizer.set_with_distributed_ttl(key, value, base_ttl)
        print(f"✓ Set '{key}': {success}")
    
    print("\n📈 3. TTL Distribution Analysis")
    print("-" * 40)
    
    # Analyze distribution patterns
    analysis = await optimizer.analyze_expiration_patterns()
    
    if "error" not in analysis:
        stats = analysis["distribution_stats"]
        clustering = analysis["clustering_analysis"]
        
        print(f"Total Keys: {stats['total_keys']}")
        print(f"Distributed Expirations: {stats['distributed_expirations']}")
        print(f"Clustered Expirations: {stats['clustered_expirations']}")
        print(f"Average Jitter: {stats['avg_jitter_ms']:.1f}ms")
        print(f"Clustering Score: {clustering['clustering_score']:.3f}")
        print(f"Distribution Type: {clustering['distribution_type']}")
    
    print("\n📊 4. TTL Distribution Chart")
    print("-" * 40)
    
    # Generate distribution chart
    chart = optimizer.generate_ttl_distribution_chart(chart_width=50)
    print(chart)
    
    print("\n⚡ 5. Clustering vs Distribution Comparison")
    print("-" * 40)
    
    # Demonstrate clustering vs distribution
    comparison = await optimizer.demonstrate_clustering_vs_distribution(
        num_keys=20, base_ttl_seconds=5
    )
    
    print("Test Parameters:")
    params = comparison["test_parameters"]
    print(f"  Keys: {params['num_keys']}")
    print(f"  Base TTL: {params['base_ttl_seconds']}s")
    print(f"  Jitter Range: ±{params['jitter_range_ms']}ms")
    
    print("\nClustered Results:")
    clustered = comparison["clustered_results"]
    print(f"  Setup Time: {clustered['setup_time_ms']:.2f}ms")
    print(f"  Clustering Score: {clustered['clustering_score']:.3f}")
    print(f"  Distribution Type: {clustered['distribution_type']}")
    
    print("\nDistributed Results:")
    distributed = comparison["distributed_results"]
    print(f"  Setup Time: {distributed['setup_time_ms']:.2f}ms")
    print(f"  Clustering Score: {distributed['clustering_score']:.3f}")
    print(f"  Distribution Type: {distributed['distribution_type']}")
    
    print("\nPerformance Impact:")
    impact = comparison["performance_impact"]
    print(f"  Setup Time Difference: {impact['setup_time_difference_ms']:.2f}ms")
    print(f"  Clustering Improvement: {impact['clustering_improvement']:.3f}")
    
    print(f"\nRecommendation: {comparison['recommendation']}")
    
    print("\n🔧 6. Configuration Management")
    print("-" * 40)
    
    # Demonstrate configuration
    current_stats = await optimizer.get_current_stats()
    config = current_stats["configuration"]
    
    print("Current Configuration:")
    print(f"  Base TTL: {config['base_ttl_ms']}ms")
    print(f"  Jitter Range: ±{config['jitter_range_ms']}ms")
    print(f"  Clustering Prevention: {config['clustering_prevention_enabled']}")
    
    # Toggle clustering prevention
    print("\nToggling clustering prevention...")
    new_state = optimizer.toggle_clustering_prevention()
    print(f"  New State: {new_state}")
    
    # Configure jitter
    print("\nConfiguring jitter range...")
    optimizer.configure_jitter(2000)  # ±2 seconds
    print(f"  New Jitter Range: ±{optimizer.jitter_range_ms}ms")
    
    print("\n✅ TTL Optimizer Demo Complete!")
    print("=" * 50)
    
    return optimizer


async def main():
    """Main demo function."""
    try:
        optimizer = await demo_ttl_optimizer()
        
        print("\n💡 Key Benefits of TTL Distribution:")
        print("  • Prevents cache expiration clustering")
        print("  • Reduces cache stampede risk")
        print("  • Improves system performance stability")
        print("  • Provides millisecond-level precision")
        print("  • Offers configurable jitter ranges")
        
        print("\n🎯 Use Cases:")
        print("  • High-traffic cache keys")
        print("  • External API response caching")
        print("  • Session management")
        print("  • Database query result caching")
        print("  • Real-time data with TTL requirements")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))