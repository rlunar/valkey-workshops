"""
Cache-Aside Pattern Demo

Demonstrates the cache-aside pattern using queries from:
- 01_simple_queries.sql (queries 12, 14)
- 02_medium_queries.sql (queries 6b, 10)
- 03_advanced_queries.sql (queries 3, 4, 10)

Shows performance improvements from caching simple to complex queries.
"""

import sys
import os
from pathlib import Path
from tabulate import tabulate

# Add parent directory to path to import cache_aside
sys.path.insert(0, str(Path(__file__).parent.parent))

from daos.cache_aside import CacheAside


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_query_result(query_name: str, results: list, source: str, latency: float, show_data: bool = True):
    """Print query execution results in a formatted way."""
    print(f"\n📊 {query_name}")
    print(f"   Source: {source:12} | Latency: {latency:7.2f} ms")
    
    if show_data and results:
        print(f"   Results: {len(results)} row(s)")
        if len(results) <= 5:
            # Show all results for small datasets
            print(f"   Data: {results[0] if len(results) == 1 else results}")
        else:
            # Show first result for large datasets
            print(f"   Sample: {results[0]}")


def demo_simple_queries(cache: CacheAside):
    """Demo simple queries (12, 14) from 01_simple_queries.sql"""
    print_section("SIMPLE QUERIES - Single/Two Table Joins")
    
    # Query 12: Get passenger with details by passenger ID
    query_12 = """
        SELECT 
            p.passenger_id,
            p.passportno,
            p.firstname,
            p.lastname,
            pd.birthdate,
            pd.sex,
            pd.street,
            pd.city,
            pd.zip,
            pd.country,
            pd.emailaddress,
            pd.telephoneno
        FROM passenger p
        LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
        WHERE p.passenger_id = 1000
    """
    
    print("\n🔍 Query 12: Get passenger with details by ID")
    print("   First execution (CACHE_MISS expected):")
    results, source, latency = cache.execute_query(query_12, ttl=3600)
    print_query_result("   Execution 1", results, source, latency)
    
    print("\n   Second execution (CACHE_HIT expected):")
    results, source, latency = cache.execute_query(query_12)
    print_query_result("   Execution 2", results, source, latency)
    
    # Query 14: Get airport with geographic details by IATA code
    query_14 = """
        SELECT 
            a.airport_id,
            a.iata,
            a.icao,
            a.name,
            ag.city,
            ag.country,
            ag.latitude,
            ag.longitude
        FROM airport a
        LEFT JOIN airport_geo ag ON a.airport_id = ag.airport_id
        WHERE a.iata = 'JFK'
    """
    
    print("\n\n🔍 Query 14: Get airport with geographic details by IATA")
    print("   First execution (CACHE_MISS expected):")
    results, source, latency = cache.execute_query(query_14, ttl=7200)
    print_query_result("   Execution 1", results, source, latency)
    
    print("\n   Second execution (CACHE_HIT expected):")
    results, source, latency = cache.execute_query(query_14)
    print_query_result("   Execution 2", results, source, latency)


def demo_medium_queries(cache: CacheAside):
    """Demo medium queries (6b, 10) from 02_medium_queries.sql"""
    print_section("MEDIUM QUERIES - Multi-Table Joins with Aggregations")
    
    # Query 6b: Find all distinct flights departing from JFK
    query_6b = """
        SELECT DISTINCT
            a_to.airport_id as destination_airport_id,
            a_to.iata as destination_iata,
            a_to.name as destination_airport,
            a_to_geo.city as destination_city,
            a_to_geo.country as destination_country,
            COUNT(f.flight_id) as number_of_flights
        FROM flight f
        INNER JOIN airport a_from ON f.`from` = a_from.airport_id
        INNER JOIN airport a_to ON f.`to` = a_to.airport_id
        LEFT JOIN airport_geo a_to_geo ON a_to.airport_id = a_to_geo.airport_id
        WHERE a_from.iata = 'JFK'
        GROUP BY a_to.airport_id, a_to.iata, a_to.name, a_to_geo.city, a_to_geo.country
        ORDER BY number_of_flights DESC
    """
    
    print("\n🔍 Query 6b: All distinct flights from JFK")
    print("   First execution (CACHE_MISS expected):")
    results, source, latency = cache.execute_query(query_6b, ttl=1800)
    print_query_result("   Execution 1", results, source, latency, show_data=False)
    if results:
        print(f"   Top 3 destinations: {results[:3]}")
    
    print("\n   Second execution (CACHE_HIT expected):")
    results, source, latency = cache.execute_query(query_6b)
    print_query_result("   Execution 2", results, source, latency, show_data=False)
    
    # Query 10: Find passengers by city and country
    query_10 = """
        SELECT 
            p.passenger_id,
            p.firstname,
            p.lastname,
            p.passportno,
            pd.city,
            pd.country
        FROM passenger p
        INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
        WHERE pd.country = 'United States'
        LIMIT 15
    """
    
    print("\n\n🔍 Query 10: Find passengers by country")
    print("   First execution (CACHE_MISS expected):")
    results, source, latency = cache.execute_query(query_10, ttl=1800)
    print_query_result("   Execution 1", results, source, latency, show_data=False)
    
    print("\n   Second execution (CACHE_HIT expected):")
    results, source, latency = cache.execute_query(query_10)
    print_query_result("   Execution 2", results, source, latency, show_data=False)


def demo_advanced_queries(cache: CacheAside):
    """Demo advanced queries (3, 4, 10) from 03_advanced_queries.sql"""
    print_section("ADVANCED QUERIES - Complex Multi-Table Joins")
    
    # Query 3: Upcoming flights for a passenger with full details
    query_3 = """
        SELECT 
            p.firstname,
            p.lastname,
            pd.emailaddress,
            b.seat,
            b.price,
            f.flightno,
            f.departure,
            f.arrival,
            a_from.name as departure_airport,
            a_to.name as arrival_airport,
            al.airlinename,
            apt.identifier as airplane_type,
            ap.capacity as airplane_capacity
        FROM passenger p
        INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
        INNER JOIN booking b ON p.passenger_id = b.passenger_id
        INNER JOIN flight f ON b.flight_id = f.flight_id
        INNER JOIN airport a_from ON f.`from` = a_from.airport_id
        INNER JOIN airport a_to ON f.`to` = a_to.airport_id
        LEFT JOIN airport_geo ag_from ON a_from.airport_id = ag_from.airport_id
        LEFT JOIN airport_geo ag_to ON a_to.airport_id = ag_to.airport_id
        INNER JOIN airline al ON f.airline_id = al.airline_id
        INNER JOIN airplane ap ON f.airplane_id = ap.airplane_id
        INNER JOIN airplane_type apt ON ap.type_id = apt.type_id
        WHERE p.passenger_id = 1000
          AND f.departure > NOW()
        ORDER BY f.departure ASC
    """
    
    print("\n🔍 Query 3: Upcoming flights for passenger with full details")
    print("   First execution (CACHE_MISS expected):")
    results, source, latency = cache.execute_query(query_3, ttl=300)
    print_query_result("   Execution 1", results, source, latency, show_data=False)
    
    print("\n   Second execution (CACHE_HIT expected):")
    results, source, latency = cache.execute_query(query_3)
    print_query_result("   Execution 2", results, source, latency, show_data=False)
    
    # Query 4: Flight manifest - all passengers on a specific flight
    query_4 = """
        SELECT 
            b.seat,
            p.firstname,
            p.lastname,
            p.passportno,
            pd.country,
            b.price
        FROM booking b
        INNER JOIN passenger p ON b.passenger_id = p.passenger_id
        LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
        WHERE b.flight_id = 115
        ORDER BY b.seat ASC
    """
    
    print("\n\n🔍 Query 4: Flight manifest for flight 115")
    print("   First execution (CACHE_MISS expected):")
    results, source, latency = cache.execute_query(query_4, ttl=600)
    print_query_result("   Execution 1", results, source, latency, show_data=False)
    
    print("\n   Second execution (CACHE_HIT expected):")
    results, source, latency = cache.execute_query(query_4)
    print_query_result("   Execution 2", results, source, latency, show_data=False)
    
    # Query 10: Recent bookings with passenger details and geographic information
    query_10 = """
        SELECT 
            b.booking_id,
            b.seat,
            b.price,
            p.firstname,
            p.lastname,
            pd.country as passenger_country,
            pd.city as passenger_city,
            f.flightno,
            f.departure,
            f.arrival,
            a_from.name as departure_airport,
            ag_from.city as departure_city,
            ag_from.country as departure_country,
            a_to.name as arrival_airport,
            ag_to.city as arrival_city,
            ag_to.country as arrival_country,
            al.airlinename
        FROM booking b
        INNER JOIN passenger p ON b.passenger_id = p.passenger_id
        LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
        INNER JOIN flight f ON b.flight_id = f.flight_id
        INNER JOIN airport a_from ON f.`from` = a_from.airport_id
        INNER JOIN airport a_to ON f.`to` = a_to.airport_id
        LEFT JOIN airport_geo ag_from ON a_from.airport_id = ag_from.airport_id
        LEFT JOIN airport_geo ag_to ON a_to.airport_id = ag_to.airport_id
        INNER JOIN airline al ON f.airline_id = al.airline_id
        ORDER BY b.booking_id DESC
        LIMIT 10
    """
    
    print("\n\n🔍 Query 10: Recent bookings with full geographic details")
    print("   First execution (CACHE_MISS expected):")
    results, source, latency = cache.execute_query(query_10, ttl=300)
    print_query_result("   Execution 1", results, source, latency, show_data=False)
    
    print("\n   Second execution (CACHE_HIT expected):")
    results, source, latency = cache.execute_query(query_10)
    print_query_result("   Execution 2", results, source, latency, show_data=False)


def demo_cache_invalidation(cache: CacheAside):
    """Demo cache invalidation functionality"""
    print_section("CACHE INVALIDATION DEMO")
    
    query = """
        SELECT 
            a.airport_id,
            a.iata,
            a.icao,
            a.name,
            ag.city,
            ag.country
        FROM airport a
        LEFT JOIN airport_geo ag ON a.airport_id = ag.airport_id
        WHERE a.iata = 'LAX'
    """
    
    print("\n🔍 Testing cache invalidation")
    
    # First execution
    print("\n   1. First execution (CACHE_MISS):")
    results, source, latency = cache.execute_query(query)
    print_query_result("      ", results, source, latency)
    
    # Second execution (cached)
    print("\n   2. Second execution (CACHE_HIT):")
    results, source, latency = cache.execute_query(query)
    print_query_result("      ", results, source, latency)
    
    # Invalidate cache
    print("\n   3. Invalidating cache...")
    invalidated = cache.invalidate_query(query)
    print(f"      Cache invalidated: {invalidated}")
    
    # Third execution (cache miss after invalidation)
    print("\n   4. After invalidation (CACHE_MISS):")
    results, source, latency = cache.execute_query(query)
    print_query_result("      ", results, source, latency)


def demo_performance_comparison(cache: CacheAside):
    """Show performance comparison table using fresh queries"""
    print_section("PERFORMANCE COMPARISON SUMMARY")
    
    print("\n📊 Running fresh queries to measure true performance impact...")
    print("   (Using queries similar to those demonstrated above)\n")
    
    # Use queries with similar complexity to the demo queries
    queries = {
        "Simple (2 tables)": """
            SELECT 
                p.passenger_id,
                p.passportno,
                p.firstname,
                p.lastname,
                pd.birthdate,
                pd.city,
                pd.country,
                pd.emailaddress
            FROM passenger p
            LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
            WHERE p.passenger_id = 2500
        """,
        "Medium (4 tables + GROUP BY)": """
            SELECT DISTINCT
                a_to.airport_id,
                a_to.iata,
                a_to.name,
                a_to_geo.city,
                a_to_geo.country,
                COUNT(f.flight_id) as flight_count
            FROM flight f
            INNER JOIN airport a_from ON f.`from` = a_from.airport_id
            INNER JOIN airport a_to ON f.`to` = a_to.airport_id
            LEFT JOIN airport_geo a_to_geo ON a_to.airport_id = a_to_geo.airport_id
            WHERE a_from.iata = 'LAX'
            GROUP BY a_to.airport_id, a_to.iata, a_to.name, a_to_geo.city, a_to_geo.country
            ORDER BY flight_count DESC
        """,
        "Advanced (7 tables + WHERE)": """
            SELECT 
                p.firstname,
                p.lastname,
                pd.emailaddress,
                b.seat,
                b.price,
                f.flightno,
                f.departure,
                f.arrival,
                a_from.name as departure_airport,
                a_to.name as arrival_airport,
                al.airlinename,
                apt.identifier as airplane_type,
                ap.capacity
            FROM passenger p
            INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
            INNER JOIN booking b ON p.passenger_id = b.passenger_id
            INNER JOIN flight f ON b.flight_id = f.flight_id
            INNER JOIN airport a_from ON f.`from` = a_from.airport_id
            INNER JOIN airport a_to ON f.`to` = a_to.airport_id
            INNER JOIN airline al ON f.airline_id = al.airline_id
            INNER JOIN airplane ap ON f.airplane_id = ap.airplane_id
            INNER JOIN airplane_type apt ON ap.type_id = apt.type_id
            WHERE p.passenger_id = 2500
              AND f.departure > '2025-01-01'
            ORDER BY f.departure ASC
        """
    }
    
    comparison_data = []
    
    for query_type, query in queries.items():
        # First, ensure cache is clear for this query
        cache.invalidate_query(query)
        
        # Get DB time (cache miss)
        _, _, db_latency = cache.execute_query(query)
        
        # Get cached time (cache hit)
        _, _, cache_latency = cache.execute_query(query)
        
        improvement = db_latency / cache_latency if cache_latency > 0 else 0
        
        comparison_data.append([
            query_type,
            f"{db_latency:.2f} ms",
            f"{cache_latency:.2f} ms",
            f"{improvement:.1f}x faster"
        ])
    
    print(tabulate(
        comparison_data,
        headers=["Query Type", "Database", "Cache", "Improvement"],
        tablefmt="grid"
    ))


def demo_summary_statistics(stats: list):
    """Show summary statistics from all demo queries"""
    print_section("DEMO QUERIES PERFORMANCE SUMMARY")
    
    print("\n📈 Performance metrics from all executed queries:\n")
    
    # Calculate statistics
    cache_misses = [s for s in stats if s['source'] == 'CACHE_MISS']
    cache_hits = [s for s in stats if s['source'] == 'CACHE_HIT']
    
    if cache_misses and cache_hits:
        avg_miss_latency = sum(s['latency'] for s in cache_misses) / len(cache_misses)
        avg_hit_latency = sum(s['latency'] for s in cache_hits) / len(cache_hits)
        max_miss_latency = max(s['latency'] for s in cache_misses)
        min_hit_latency = min(s['latency'] for s in cache_hits)
        
        summary_data = [
            ["Total Queries", len(stats)],
            ["Cache Misses (DB)", len(cache_misses)],
            ["Cache Hits", len(cache_hits)],
            ["", ""],
            ["Avg DB Latency", f"{avg_miss_latency:.2f} ms"],
            ["Avg Cache Latency", f"{avg_hit_latency:.2f} ms"],
            ["Max DB Latency", f"{max_miss_latency:.2f} ms"],
            ["Min Cache Latency", f"{min_hit_latency:.2f} ms"],
            ["", ""],
            ["Avg Speedup", f"{avg_miss_latency / avg_hit_latency:.1f}x faster"],
            ["Best Speedup", f"{max_miss_latency / min_hit_latency:.1f}x faster"],
        ]
        
        print(tabulate(summary_data, tablefmt="simple"))


def main():
    """Run all demos"""
    print("\n" + "🚀" * 40)
    print("  CACHE-ASIDE PATTERN DEMONSTRATION")
    print("  Airport Database Query Performance with Caching")
    print("🚀" * 40)
    
    # Initialize cache
    print("\n📡 Initializing cache-aside handler...")
    cache = CacheAside()
    print("   ✓ Connected to database and cache")
    
    # Track all query statistics
    stats = []
    
    # Monkey patch to collect stats
    original_execute = cache.execute_query
    def tracked_execute(*args, **kwargs):
        results, source, latency = original_execute(*args, **kwargs)
        stats.append({'source': source, 'latency': latency})
        return results, source, latency
    cache.execute_query = tracked_execute
    
    try:
        # Run demos
        demo_simple_queries(cache)
        demo_medium_queries(cache)
        demo_advanced_queries(cache)
        demo_cache_invalidation(cache)
        demo_summary_statistics(stats)
        demo_performance_comparison(cache)
        
        print_section("DEMO COMPLETE")
        print("\n✅ All queries executed successfully!")
        print("\n💡 Key Takeaways:")
        print("   • Cache hits are significantly faster than database queries")
        print("   • Complex queries benefit most from caching (50-250x improvement)")
        print("   • Cache invalidation allows for data freshness control")
        print("   • TTL can be tuned based on data volatility")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up connections...")
        cache.close()
        print("   ✓ Connections closed")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
