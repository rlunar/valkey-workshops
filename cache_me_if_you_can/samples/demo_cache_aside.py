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
from dotenv import load_dotenv
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.prompt import Confirm
from tqdm import tqdm
import time

# Load environment variables
load_dotenv()

# Add parent directory to path to import cache_aside
sys.path.insert(0, str(Path(__file__).parent.parent))

from daos.cache_aside import CacheAside

# Initialize typer app and rich console
app = typer.Typer(help="Cache-Aside Pattern Demonstration")
console = Console()

# Global verbose flag
VERBOSE = False


def print_section(title: str):
    """Print a formatted section header using rich."""
    console.print()
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", box=box.DOUBLE))


def get_cache_key(query: str) -> str:
    """Generate cache key from query (same logic as CacheAside)."""
    import hashlib
    query_hash = hashlib.sha256(query.encode()).hexdigest()
    return f"query:{query_hash}"


def print_query_info(query: str, cache_key: str = None):
    """Print query and cache key information in verbose mode."""
    if VERBOSE:
        console.print("\n[dim]─── Query Details ───[/dim]")
        console.print(Panel(
            f"[cyan]{query.strip()}[/cyan]",
            title="[bold]SQL Query[/bold]",
            border_style="dim",
            box=box.ROUNDED
        ))
        if cache_key:
            console.print(f"[dim]Cache Key:[/dim] [yellow]{cache_key}[/yellow]")
            console.print(f"[dim]Key Hash:[/dim] [yellow]{cache_key.split(':')[1][:16]}...[/yellow]")


def print_query_result(query_name: str, results: list, source: str, latency: float, show_data: bool = True, show_query: bool = False, query: str = None, cache_key: str = None):
    """Print query execution results in a formatted way using rich."""
    # Show query details if verbose and show_query is True
    if VERBOSE and show_query and query:
        print_query_info(query, cache_key)
    
    # Color code based on source
    source_color = "green" if source == "CACHE_HIT" else "yellow"
    icon = "✓" if source == "CACHE_HIT" else "⚡"
    
    console.print(f"\n{icon} [bold]{query_name}[/bold]")
    console.print(f"   Source: [{source_color}]{source:12}[/{source_color}] | Latency: [magenta]{latency:7.2f} ms[/magenta]")
    
    if show_data and results:
        console.print(f"   Results: [cyan]{len(results)} row(s)[/cyan]")
        if len(results) <= 5 and len(results) > 0:
            # Show all results for small datasets
            console.print(f"   Data: {results[0] if len(results) == 1 else results[:2]}")
        elif len(results) > 0:
            # Show first result for large datasets
            console.print(f"   Sample: {results[0]}")


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
    
    cache_key_12 = get_cache_key(query_12)
    
    console.print("\n🔍 [bold]Query 12: Get passenger with details by ID[/bold]")
    
    # Show query once in verbose mode
    if VERBOSE:
        print_query_info(query_12, cache_key_12)
    
    console.print("\n   First execution (CACHE_MISS ❌ expected):")
    results, source, latency = cache.execute_query(query_12, ttl=3600)
    print_query_result("   Execution 1", results, source, latency, show_query=False)
    
    console.print("\n   Second execution (CACHE_HIT ✅ expected):")
    results, source, latency = cache.execute_query(query_12)
    print_query_result("   Execution 2", results, source, latency, show_query=False)
    
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
    
    cache_key_14 = get_cache_key(query_14)
    
    console.print("\n\n🔍 [bold]Query 14: Get airport with geographic details by IATA[/bold]")
    
    # Show query once in verbose mode
    if VERBOSE:
        print_query_info(query_14, cache_key_14)
    
    console.print("\n   First execution (CACHE_MISS ❌ expected):")
    results, source, latency = cache.execute_query(query_14, ttl=7200)
    print_query_result("   Execution 1", results, source, latency, show_query=False)
    
    console.print("\n   Second execution (CACHE_HIT ✅ expected):")
    results, source, latency = cache.execute_query(query_14)
    print_query_result("   Execution 2", results, source, latency, show_query=False)


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
    
    cache_key_6b = get_cache_key(query_6b)
    
    console.print("\n🔍 [bold]Query 6b: All distinct flights from JFK[/bold]")
    
    # Show query once in verbose mode
    if VERBOSE:
        print_query_info(query_6b, cache_key_6b)
    
    console.print("\n   First execution (CACHE_MISS ❌ expected):")
    results, source, latency = cache.execute_query(query_6b, ttl=1800)
    print_query_result("   Execution 1", results, source, latency, show_data=False, show_query=False)
    if results:
        console.print(f"   Top 3 destinations: {results[:3]}")
    
    console.print("\n   Second execution (CACHE_HIT ✅ expected):")
    results, source, latency = cache.execute_query(query_6b)
    print_query_result("   Execution 2", results, source, latency, show_data=False, show_query=False)
    
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
    
    cache_key_10 = get_cache_key(query_10)
    
    console.print("\n\n🔍 [bold]Query 10: Find passengers by country[/bold]")
    
    # Show query once in verbose mode
    if VERBOSE:
        print_query_info(query_10, cache_key_10)
    
    console.print("\n   First execution (CACHE_MISS ❌ expected):")
    results, source, latency = cache.execute_query(query_10, ttl=1800)
    print_query_result("   Execution 1", results, source, latency, show_data=False, show_query=False)
    
    console.print("\n   Second execution (CACHE_HIT ✅ expected):")
    results, source, latency = cache.execute_query(query_10)
    print_query_result("   Execution 2", results, source, latency, show_data=False, show_query=False)


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
    
    cache_key_3 = get_cache_key(query_3)
    
    console.print("\n🔍 [bold]Query 3: Upcoming flights for passenger with full details[/bold]")
    
    # Show query once in verbose mode
    if VERBOSE:
        print_query_info(query_3, cache_key_3)
    
    console.print("\n   First execution (CACHE_MISS ❌ expected):")
    results, source, latency = cache.execute_query(query_3, ttl=300)
    print_query_result("   Execution 1", results, source, latency, show_data=False, show_query=False)
    
    console.print("\n   Second execution (CACHE_HIT ✅ expected):")
    results, source, latency = cache.execute_query(query_3)
    print_query_result("   Execution 2", results, source, latency, show_data=False, show_query=False)
    
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
    
    cache_key_4 = get_cache_key(query_4)
    
    console.print("\n\n🔍 [bold]Query 4: Flight manifest for flight 115[/bold]")
    
    # Show query once in verbose mode
    if VERBOSE:
        print_query_info(query_4, cache_key_4)
    
    console.print("\n   First execution (CACHE_MISS ❌ expected):")
    results, source, latency = cache.execute_query(query_4, ttl=600)
    print_query_result("   Execution 1", results, source, latency, show_data=False, show_query=False)
    
    console.print("\n   Second execution (CACHE_HIT ✅ expected):")
    results, source, latency = cache.execute_query(query_4)
    print_query_result("   Execution 2", results, source, latency, show_data=False, show_query=False)
    
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
    
    cache_key_10 = get_cache_key(query_10)
    
    console.print("\n\n🔍 [bold]Query 10: Recent bookings with full geographic details[/bold]")
    
    # Show query once in verbose mode
    if VERBOSE:
        print_query_info(query_10, cache_key_10)
    
    console.print("\n   First execution (CACHE_MISS ❌ expected):")
    results, source, latency = cache.execute_query(query_10, ttl=300)
    print_query_result("   Execution 1", results, source, latency, show_data=False, show_query=False)
    
    console.print("\n   Second execution (CACHE_HIT ✅ expected):")
    results, source, latency = cache.execute_query(query_10)
    print_query_result("   Execution 2", results, source, latency, show_data=False, show_query=False)


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
    print("\n   1. First execution (CACHE_MISS ❌):")
    results, source, latency = cache.execute_query(query)
    print_query_result("      ", results, source, latency)
    
    # Second execution (cached)
    print("\n   2. Second execution (CACHE_HIT ✅):")
    results, source, latency = cache.execute_query(query)
    print_query_result("      ", results, source, latency)
    
    # Invalidate cache
    print("\n   3. Invalidating cache...")
    invalidated = cache.invalidate_query(query)
    print(f"      Cache invalidated: {invalidated}")
    
    # Third execution (cache miss after invalidation)
    print("\n   4. After invalidation (CACHE_MISS ❌):")
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
            f"{db_latency:.3f} ms",
            f"{cache_latency:.3f} ms",
            f"{improvement:.2f}x faster"
        ])
    
    # Create rich table
    table = Table(title="📊 Performance Comparison", box=box.ROUNDED, show_lines=True)
    table.add_column("Query Type", style="cyan", no_wrap=True)
    table.add_column("Database", style="yellow", justify="right")
    table.add_column("Cache", style="green", justify="right")
    table.add_column("Improvement", style="magenta bold", justify="right")
    
    for row in comparison_data:
        table.add_row(*row)
    
    console.print(table)


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
            ["Avg DB Latency", f"{avg_miss_latency:.3f} ms"],
            ["Avg Cache Latency", f"{avg_hit_latency:.3f} ms"],
            ["Max DB Latency", f"{max_miss_latency:.3f} ms"],
            ["Min Cache Latency", f"{min_hit_latency:.3f} ms"],
            ["", ""],
            ["Avg Speedup", f"{avg_miss_latency / avg_hit_latency:.2f}x faster"],
            ["Best Speedup", f"{max_miss_latency / min_hit_latency:.2f}x faster"],
        ]
        
        # Create rich table for summary
        table = Table(title="📈 Performance Metrics", box=box.SIMPLE, show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow", justify="right")
        
        for row in summary_data:
            if row[0] == "":
                table.add_row("", "")  # Empty row for spacing
            else:
                table.add_row(row[0], str(row[1]))
        
        console.print(table)


@app.command()
def run(
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Run demo step-by-step with prompts"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show SQL queries and cache keys"
    )
):
    """Run the cache-aside pattern demonstration"""
    
    # Set global verbose flag
    global VERBOSE
    VERBOSE = verbose
    
    if VERBOSE:
        console.print("[dim]Verbose mode enabled - showing SQL queries and cache keys[/dim]\n")
    
    # Print header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]CACHE-ASIDE PATTERN DEMONSTRATION[/bold cyan]\n"
        "[yellow]Airport Database Query Performance with Caching[/yellow]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    # Initialize cache with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Initializing cache-aside handler...", total=None)
        cache = CacheAside()
        progress.update(task, completed=True)
    
    console.print("[green]✓[/green] Connected to database and cache\n")
    
    # Track all query statistics
    stats = []
    
    # Monkey patch to collect stats
    original_execute = cache.execute_query
    def tracked_execute(*args, **kwargs):
        results, source, latency = original_execute(*args, **kwargs)
        stats.append({'source': source, 'latency': latency})
        return results, source, latency
    cache.execute_query = tracked_execute
    
    # Define demo steps
    demo_steps = [
        ("Simple Queries", lambda: demo_simple_queries(cache)),
        ("Medium Queries", lambda: demo_medium_queries(cache)),
        ("Advanced Queries", lambda: demo_advanced_queries(cache)),
        ("Cache Invalidation", lambda: demo_cache_invalidation(cache)),
        ("Summary Statistics", lambda: demo_summary_statistics(stats)),
        ("Performance Comparison", lambda: demo_performance_comparison(cache)),
    ]
    
    try:
        if interactive:
            # Interactive mode - run step by step
            console.print("[bold yellow]Interactive Mode:[/bold yellow] Press Enter to continue after each step\n")
            
            for step_name, step_func in demo_steps:
                console.print(f"[bold]→ Next: {step_name}[/bold]")
                if not Confirm.ask("Continue?", default=True):
                    console.print("[yellow]Skipping...[/yellow]")
                    continue
                
                step_func()
                console.print()
        else:
            # Automatic mode - run all steps with progress bar
            console.print("[bold green]Automatic Mode:[/bold green] Running all demo steps\n")
            
            for step_name, step_func in tqdm(demo_steps, desc="Demo Progress", unit="step"):
                step_func()
                time.sleep(0.5)  # Brief pause for readability
        
        # Final summary
        print_section("DEMO COMPLETE")
        console.print("\n[green]✅ All queries executed successfully![/green]\n")
        
        # Key takeaways in a nice table
        takeaways_table = Table(title="💡 Key Takeaways", box=box.ROUNDED, show_header=False)
        takeaways_table.add_column("", style="cyan")
        takeaways_table.add_row("• Cache hits are significantly faster than database queries")
        takeaways_table.add_row("• Complex queries benefit most from caching (50-250x improvement)")
        takeaways_table.add_row("• Cache invalidation allows for data freshness control")
        takeaways_table.add_row("• TTL can be tuned based on data volatility")
        console.print(takeaways_table)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error during demo: {e}[/red]")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        console.print("\n[cyan]🧹 Cleaning up connections...[/cyan]")
        cache.close()
        console.print("[green]✓[/green] Connections closed\n")


if __name__ == "__main__":
    app()
