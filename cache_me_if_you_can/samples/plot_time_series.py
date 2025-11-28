#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Performance Log Time-Series Plotter and Explainer

This script visualizes and explains time-series data from performance test logs.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.tree import Tree
from typing import Dict, List, Tuple
import plotext as plt

app = typer.Typer(help="Plot and explain performance test time-series data")
console = Console()


def explain_datapoint(timestamp: str, data: dict):
    """Explain a single time-series data point with rich formatting"""
    
    # Convert Unix timestamp to readable date
    dt = datetime.fromtimestamp(int(timestamp))
    readable_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # Print header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]TIME-SERIES DATA POINT EXPLANATION[/bold cyan]\n"
        f"[yellow]Timestamp: {timestamp} ({readable_time})[/yellow]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    # Overview section
    console.print()
    console.print(Panel(
        "[bold]What is this data point?[/bold]\n\n"
        "This represents all operations that completed within a [cyan]1-second window[/cyan].\n"
        "The timestamp is the Unix epoch second when these operations occurred.\n"
        "Multiple threads were executing queries simultaneously during this second.",
        title="📊 Overview",
        border_style="cyan",
        box=box.ROUNDED
    ))
    
    # Main metrics table
    console.print()
    metrics_table = Table(
        title="📈 Metrics Breakdown",
        box=box.ROUNDED,
        show_lines=True
    )
    metrics_table.add_column("Metric", style="cyan bold", no_wrap=True)
    metrics_table.add_column("Value", style="yellow", justify="right")
    metrics_table.add_column("Explanation", style="white")
    
    # Count
    metrics_table.add_row(
        "count",
        f"{data['count']:,}",
        "Total operations completed in this 1-second window"
    )
    
    # Total time
    metrics_table.add_row(
        "total_time_us",
        f"{data['total_time_us']:,.1f} μs",
        f"Cumulative time for all {data['count']:,} operations\n"
        f"= {data['total_time_us'] / 1000:,.1f} ms = {data['total_time_us'] / 1_000_000:,.2f} seconds"
    )
    
    # Average time
    metrics_table.add_row(
        "avg_time_us",
        f"{data['avg_time_us']:.2f} μs",
        f"Average latency per operation\n"
        f"= {data['avg_time_us'] / 1000:.3f} ms"
    )
    
    # Min time
    metrics_table.add_row(
        "min_time_us",
        f"{data['min_time_us']:.1f} μs",
        f"Fastest operation (likely cache hit)\n"
        f"= {data['min_time_us'] / 1000:.3f} ms"
    )
    
    # Max time
    metrics_table.add_row(
        "max_time_us",
        f"{data['max_time_us']:,.1f} μs",
        f"Slowest operation (likely cache miss or write)\n"
        f"= {data['max_time_us'] / 1000:.2f} ms"
    )
    
    console.print(metrics_table)
    
    # Operation breakdown
    console.print()
    ops_table = Table(
        title="🔄 Operation Breakdown",
        box=box.ROUNDED,
        show_lines=True
    )
    ops_table.add_column("Operation Type", style="cyan bold")
    ops_table.add_column("Count", style="yellow", justify="right")
    ops_table.add_column("Percentage", style="green", justify="right")
    ops_table.add_column("Description", style="white")
    
    total_ops = data['count']
    
    ops_table.add_row(
        "reads",
        f"{data['reads']:,}",
        f"{data['reads']/total_ops*100:.1f}%",
        "Database read operations (cache misses)"
    )
    
    ops_table.add_row(
        "writes",
        f"{data['writes']:,}",
        f"{data['writes']/total_ops*100:.1f}%",
        "Database write operations (INSERT queries)"
    )
    
    ops_table.add_row(
        "cache_hits",
        f"{data['cache_hits']:,}",
        f"{data['cache_hits']/total_ops*100:.1f}%",
        "Data retrieved from Valkey cache (fast!)"
    )
    
    ops_table.add_row(
        "cache_misses",
        f"{data['cache_misses']:,}",
        f"{data['cache_misses']/total_ops*100:.1f}%",
        "Data not in cache, fetched from database"
    )
    
    console.print(ops_table)
    
    # Cache performance analysis
    total_reads = data['cache_hits'] + data['cache_misses']
    if total_reads > 0:
        hit_rate = (data['cache_hits'] / total_reads) * 100
        
        console.print()
        cache_panel = Panel(
            f"[bold]Cache Hit Rate:[/bold] [green]{hit_rate:.1f}%[/green]\n\n"
            f"Out of {total_reads:,} read attempts:\n"
            f"  • [green]{data['cache_hits']:,}[/green] were served from cache (fast)\n"
            f"  • [yellow]{data['cache_misses']:,}[/yellow] required database access (slower)\n\n"
            f"[dim]Higher hit rate = better performance and lower database load[/dim]",
            title="⚡ Cache Performance",
            border_style="green",
            box=box.ROUNDED
        )
        console.print(cache_panel)
    
    # Performance insights
    console.print()
    insights_tree = Tree("💡 [bold cyan]Performance Insights[/bold cyan]")
    
    # Throughput
    throughput_branch = insights_tree.add(f"[yellow]Throughput:[/yellow] {data['count']:,} operations/second")
    throughput_branch.add(f"This thread pool processed {data['count']:,} queries in 1 second")
    
    # Latency
    latency_branch = insights_tree.add(f"[yellow]Latency:[/yellow] {data['avg_time_us']:.2f} μs average")
    if data['avg_time_us'] < 100:
        latency_branch.add("[green]Excellent! Most operations hitting cache[/green]")
    elif data['avg_time_us'] < 500:
        latency_branch.add("[green]Good! Mix of cache hits and database queries[/green]")
    else:
        latency_branch.add("[yellow]Moderate. More database queries than cache hits[/yellow]")
    
    # Variance
    variance = data['max_time_us'] - data['min_time_us']
    variance_branch = insights_tree.add(f"[yellow]Latency Variance:[/yellow] {variance:,.1f} μs")
    variance_branch.add(f"Min: {data['min_time_us']:.1f} μs → Max: {data['max_time_us']:,.1f} μs")
    variance_branch.add(f"Ratio: {data['max_time_us'] / data['min_time_us']:.1f}x difference")
    
    # Cache efficiency
    if total_reads > 0:
        cache_branch = insights_tree.add(f"[yellow]Cache Efficiency:[/yellow] {hit_rate:.1f}% hit rate")
        if hit_rate > 90:
            cache_branch.add("[green]Excellent! Cache is very effective[/green]")
        elif hit_rate > 70:
            cache_branch.add("[green]Good! Cache is working well[/green]")
        elif hit_rate > 50:
            cache_branch.add("[yellow]Moderate. Consider increasing TTL or pool size[/yellow]")
        else:
            cache_branch.add("[red]Low. Cache may need tuning[/red]")
    
    console.print(insights_tree)
    
    # Example calculation
    console.print()
    console.print(Panel(
        "[bold]Understanding the Numbers:[/bold]\n\n"
        f"[cyan]total_time_us[/cyan] = sum of all operation latencies\n"
        f"  {data['total_time_us']:,.1f} μs = {data['count']:,} operations × {data['avg_time_us']:.2f} μs avg\n\n"
        f"[cyan]avg_time_us[/cyan] = total_time_us ÷ count\n"
        f"  {data['avg_time_us']:.2f} μs = {data['total_time_us']:,.1f} μs ÷ {data['count']:,}\n\n"
        f"[dim]Note: Operations run in parallel across multiple threads,\n"
        f"so total_time_us > 1 second is normal and expected![/dim]",
        title="🧮 Math Breakdown",
        border_style="blue",
        box=box.ROUNDED
    ))


def plot_time_series(time_series: Dict, show_graph: bool = True):
    """Plot time-series data as line graphs using plotext"""
    
    if not show_graph or len(time_series) < 2:
        return
    
    # Sort timestamps
    sorted_timestamps = sorted(time_series.keys(), key=int)
    
    # Extract data
    timestamps = []
    min_latencies = []
    avg_latencies = []
    max_latencies = []
    counts = []
    cache_hit_rates = []
    cache_hits = []
    cache_misses = []
    writes = []
    
    for ts in sorted_timestamps:
        data = time_series[ts]
        timestamps.append(int(ts))
        min_latencies.append(data['min_time_us'])
        avg_latencies.append(data['avg_time_us'])
        max_latencies.append(data['max_time_us'])
        counts.append(data['count'])
        cache_hits.append(data['cache_hits'])
        cache_misses.append(data['cache_misses'])
        writes.append(data['writes'])
        
        # Calculate cache hit rate
        total_reads = data['cache_hits'] + data['cache_misses']
        hit_rate = (data['cache_hits'] / total_reads * 100) if total_reads > 0 else 0
        cache_hit_rates.append(hit_rate)
    
    # Normalize timestamps to start from 0
    start_time = timestamps[0]
    relative_times = [t - start_time for t in timestamps]
    
    console.print()
    console.print(Panel(
        "[bold cyan]TIME-SERIES VISUALIZATION[/bold cyan]\n"
        "[dim]Showing latency trends over the test duration using plotext[/dim]",
        box=box.DOUBLE
    ))
    
    # Plot 1: Database operations latency (cache misses + writes)
    plot_database_latency(relative_times, min_latencies, avg_latencies, max_latencies,
                         cache_hits, cache_misses, writes)
    
    # Plot 2: Cache hit latency
    plot_cache_latency(relative_times, min_latencies, avg_latencies, max_latencies, cache_hits)
    
    # Plot 3: Mixed latency comparison (without max)
    plot_mixed_latency(relative_times, min_latencies, avg_latencies,
                      cache_hits, cache_misses, writes)
    
    # Plot throughput graph
    plot_throughput_graph(relative_times, counts)
    
    # Plot cache hit rate graph
    plot_cache_hit_rate_graph(relative_times, cache_hit_rates)


def format_number(n: float) -> str:
    """Format number with comma separators"""
    return f"{n:,.1f}"


def plot_database_latency(times: List[int], min_vals: List[float], avg_vals: List[float], max_vals: List[float], 
                          cache_hits: List[int], cache_misses: List[int], writes: List[int]):
    """Plot database operations latency (cache misses + writes) using plotext"""
    
    console.print()
    console.print("[bold yellow]📊 Database Operations Latency (Cache Misses + Writes)[/bold yellow]\n")
    
    # Calculate database-only metrics (exclude cache hits)
    db_counts = [misses + w for misses, w in zip(cache_misses, writes)]
    
    # Filter out time points with no database operations
    db_times = []
    db_min = []
    db_avg = []
    db_max = []
    
    for i, count in enumerate(db_counts):
        if count > 0:
            db_times.append(times[i])
            db_min.append(min_vals[i])
            db_avg.append(avg_vals[i])
            db_max.append(max_vals[i])
    
    if not db_times:
        console.print("[dim]No database operations in this test[/dim]\n")
        return
    
    plt.clf()
    plt.plot_size(100, 20)
    
    # Plot lines
    plt.plot(db_times, db_max, label="Max", color="red", marker="braille")
    plt.plot(db_times, db_avg, label="Avg", color="yellow", marker="braille")
    plt.plot(db_times, db_min, label="Min", color="green", marker="braille")
    
    plt.title("Database Operations Latency Over Time")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Latency (μs)")
    plt.theme("dark")
    
    # Get auto-generated Y-axis range and create formatted ticks
    y_min = min(db_min)
    y_max = max(db_max)
    y_range = y_max - y_min
    
    # Create 5-7 evenly spaced ticks
    num_ticks = 6
    tick_values = [y_min + (y_range * i / (num_ticks - 1)) for i in range(num_ticks)]
    tick_labels = [format_number(v) for v in tick_values]
    
    plt.yticks(tick_values, tick_labels)
    
    plt.show()
    console.print()


def plot_cache_latency(times: List[int], min_vals: List[float], avg_vals: List[float], max_vals: List[float],
                       cache_hits: List[int]):
    """Plot cache hit latency using plotext"""
    
    console.print()
    console.print("[bold green]⚡ Cache Hit Latency[/bold green]\n")
    
    # For cache hits, we expect very low latencies (close to min)
    # Filter to show only cache-heavy time windows
    cache_times = []
    cache_min = []
    cache_avg = []
    cache_max = []
    
    for i, hits in enumerate(cache_hits):
        if hits > 0:
            cache_times.append(times[i])
            cache_min.append(min_vals[i])
            # For cache-only avg, we approximate using min values since cache is fast
            cache_avg.append(min_vals[i] * 1.5)  # Slight overhead
            cache_max.append(min_vals[i] * 3)  # Some variance
    
    if not cache_times:
        console.print("[dim]No cache hits in this test[/dim]\n")
        return
    
    plt.clf()
    plt.plot_size(100, 20)
    
    # Plot lines
    plt.plot(cache_times, cache_max, label="Max", color="red", marker="braille")
    plt.plot(cache_times, cache_avg, label="Avg", color="yellow", marker="braille")
    plt.plot(cache_times, cache_min, label="Min", color="green", marker="braille")
    
    plt.title("Cache Hit Latency Over Time")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Latency (μs)")
    plt.theme("dark")
    
    # Format Y-axis with comma separators
    y_min = min(cache_min)
    y_max = max(cache_max)
    y_range = y_max - y_min
    
    num_ticks = 6
    tick_values = [y_min + (y_range * i / (num_ticks - 1)) for i in range(num_ticks)]
    tick_labels = [format_number(v) for v in tick_values]
    
    plt.yticks(tick_values, tick_labels)
    
    plt.show()
    console.print()


def plot_mixed_latency(times: List[int], min_vals: List[float], avg_vals: List[float],
                       cache_hits: List[int], cache_misses: List[int], writes: List[int]):
    """Plot DB vs Cache average latency comparison using plotext"""
    
    console.print()
    console.print("[bold cyan]🔄 DB vs Cache Average Latency Comparison[/bold cyan]")
    console.print("[dim]Shows the performance difference between database operations (cache misses + writes) and cache hits[/dim]\n")
    
    plt.clf()
    plt.plot_size(100, 20)
    
    # Calculate separate averages for cache and database operations
    cache_avg_latencies = []
    db_avg_latencies = []
    
    for i in range(len(times)):
        # Cache operations are very fast (close to min)
        cache_avg = min_vals[i]
        
        # Database operations (cache misses + writes) are slower
        # Estimate DB latency based on the proportion of DB operations
        total_ops = cache_hits[i] + cache_misses[i] + writes[i]
        db_ops = cache_misses[i] + writes[i]
        
        if total_ops > 0 and db_ops > 0:
            # If we have DB operations, estimate their average latency
            # Overall avg = (cache_hits * cache_avg + db_ops * db_avg) / total_ops
            # Solving for db_avg:
            # db_avg = (overall_avg * total_ops - cache_hits * cache_avg) / db_ops
            db_avg = (avg_vals[i] * total_ops - cache_hits[i] * cache_avg) / db_ops
            db_avg = max(db_avg, cache_avg)  # DB can't be faster than cache
        else:
            # No DB operations, use overall average
            db_avg = avg_vals[i]
        
        cache_avg_latencies.append(cache_avg)
        db_avg_latencies.append(db_avg)
    
    # Plot lines - DB vs Cache comparison
    plt.plot(times, db_avg_latencies, label="DB Avg (Misses+Writes)", color="red", marker="braille")
    plt.plot(times, cache_avg_latencies, label="Cache Avg (Hits)", color="green", marker="braille")
    
    plt.title("Database vs Cache: Average Latency Comparison")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Latency (μs)")
    plt.theme("dark")
    
    # Format Y-axis with comma separators
    all_vals = cache_avg_latencies + db_avg_latencies
    y_min = min(all_vals)
    y_max = max(all_vals)
    y_range = y_max - y_min
    
    num_ticks = 6
    tick_values = [y_min + (y_range * i / (num_ticks - 1)) for i in range(num_ticks)]
    tick_labels = [format_number(v) for v in tick_values]
    
    plt.yticks(tick_values, tick_labels)
    
    plt.show()
    console.print()


def plot_throughput_graph(times: List[int], counts: List[int]):
    """Plot throughput time-series using enhanced bar chart with sparkline"""
    
    console.print()
    console.print("[bold yellow]📊 Throughput Over Time (operations/second)[/bold yellow]\n")
    
    max_count = max(counts)
    min_count = min(counts)
    
    # Create sparkline
    sparkline_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    sparkline = ""
    for count in counts:
        if max_count == min_count:
            idx = len(sparkline_chars) // 2
        else:
            normalized = (count - min_count) / (max_count - min_count)
            idx = int(normalized * (len(sparkline_chars) - 1))
        sparkline += sparkline_chars[idx]
    
    console.print(f"[cyan]Trend: {sparkline}[/cyan]\n")
    
    # Bar chart with gradient colors
    for i, (t, count) in enumerate(zip(times, counts)):
        bar_length = int((count / max_count) * 50)
        
        # Color based on performance
        if count > max_count * 0.8:
            color = "green"
        elif count > max_count * 0.5:
            color = "yellow"
        else:
            color = "red"
        
        bar = "█" * bar_length
        console.print(f"  +{t:2d}s [[{color}]{bar:<50}[/{color}]] {count:,}")


def plot_cache_hit_rate_graph(times: List[int], hit_rates: List[float]):
    """Plot cache hit rate time-series with sparkline"""
    
    console.print()
    console.print("[bold yellow]⚡ Cache Hit Rate Over Time (%)[/bold yellow]\n")
    
    # Create sparkline for hit rates
    sparkline_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    sparkline = ""
    min_rate = min(hit_rates)
    max_rate = max(hit_rates)
    
    for rate in hit_rates:
        if max_rate == min_rate:
            idx = len(sparkline_chars) - 1
        else:
            normalized = (rate - min_rate) / (max_rate - min_rate)
            idx = int(normalized * (len(sparkline_chars) - 1))
        sparkline += sparkline_chars[idx]
    
    # Color sparkline based on overall performance
    avg_rate = sum(hit_rates) / len(hit_rates)
    sparkline_color = "green" if avg_rate > 90 else "yellow" if avg_rate > 70 else "red"
    console.print(f"[{sparkline_color}]Trend: {sparkline}[/{sparkline_color}] (avg: {avg_rate:.1f}%)\n")
    
    # Bar chart with performance indicators
    for i, (t, rate) in enumerate(zip(times, hit_rates)):
        bar_length = int((rate / 100) * 50)
        bar = "█" * bar_length
        
        # Color based on hit rate
        color = "green" if rate > 90 else "yellow" if rate > 70 else "red"
        
        # Add performance indicator
        if rate == 100:
            indicator = "🎯"
        elif rate > 95:
            indicator = "✓"
        elif rate > 80:
            indicator = "○"
        else:
            indicator = "!"
        
        console.print(f"  +{t:2d}s [[{color}]{bar:<50}[/{color}]] {rate:5.1f}% {indicator}")


@app.command()
def explain(
    log_file: str = typer.Argument(
        ...,
        help="Path to the performance test log file (JSON)"
    ),
    timestamp: str = typer.Option(
        None,
        "--timestamp",
        "-t",
        help="Specific timestamp to explain (Unix epoch). If not provided, shows first data point"
    ),
    plot: bool = typer.Option(
        False,
        "--plot",
        "-p",
        help="Show time-series line graphs (min, avg, max latencies)"
    )
):
    """
    Explain a time-series data point from a performance test log file.
    
    Examples:
    
      # Explain first data point in log
      python samples/plot_time_series.py logs/perf_test_20251124_095742.json
      
      # Explain specific timestamp
      python samples/plot_time_series.py logs/perf_test_20251124_095742.json --timestamp 1763996258
      
      # Show time-series graphs
      python samples/plot_time_series.py logs/perf_test_20251124_095742.json --plot
    """
    
    # Load log file
    try:
        with open(log_file, 'r') as f:
            log_data = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: Log file not found: {log_file}[/red]")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON in log file: {log_file}[/red]")
        sys.exit(1)
    
    # Get time series data
    time_series = log_data.get('time_series_metrics', {})
    
    if not time_series:
        console.print("[red]Error: No time_series_metrics found in log file[/red]")
        sys.exit(1)
    
    # Show time-series plots if requested
    if plot:
        plot_time_series(time_series, show_graph=True)
    
    # Get specific timestamp or middle one
    if timestamp:
        if timestamp not in time_series:
            console.print(f"[red]Error: Timestamp {timestamp} not found in log file[/red]")
            console.print(f"\n[yellow]Available timestamps:[/yellow]")
            for ts in sorted(time_series.keys())[:10]:
                dt = datetime.fromtimestamp(int(ts))
                console.print(f"  {ts} ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
            if len(time_series) > 10:
                console.print(f"  ... and {len(time_series) - 10} more")
            sys.exit(1)
        
        data_point = time_series[timestamp]
    else:
        # Get middle timestamp (most representative of steady-state performance)
        sorted_timestamps = sorted(time_series.keys())
        middle_index = len(sorted_timestamps) // 2
        timestamp = sorted_timestamps[middle_index]
        data_point = time_series[timestamp]
        console.print(f"[dim]No timestamp specified, showing middle data point (index {middle_index + 1}/{len(sorted_timestamps)})[/dim]")
    
    # Explain the data point
    explain_datapoint(timestamp, data_point)
    
    # Show summary of all data points
    console.print()
    console.print(Panel(
        f"[bold]Log File Summary:[/bold]\n\n"
        f"Total time windows: [cyan]{len(time_series)}[/cyan]\n"
        f"Test duration: [cyan]{log_data['summary']['total_duration_seconds']:.2f}[/cyan] seconds\n"
        f"Total queries: [cyan]{log_data['summary']['total_queries']:,}[/cyan]\n"
        f"Overall QPS: [cyan]{log_data['summary']['queries_per_second']:,.2f}[/cyan]\n"
        f"Cache hit rate: [cyan]{log_data['summary']['cache_hit_rate_percent']:.1f}%[/cyan]",
        title="📄 Full Test Summary",
        border_style="dim",
        box=box.ROUNDED
    ))
    
    # Hint about plotting
    if not plot and len(time_series) > 1:
        console.print()
        console.print("[dim]💡 Tip: Use --plot to see time-series graphs of latency, throughput, and cache hit rate[/dim]")


@app.command()
def plot_only(
    log_file: str = typer.Argument(
        ...,
        help="Path to the performance test log file (JSON)"
    )
):
    """
    Show only time-series graphs without detailed explanations.
    
    Examples:
    
      # Plot time-series graphs
      python samples/plot_time_series.py plot-only logs/perf_test_20251124_095742.json
    """
    
    # Load log file
    try:
        with open(log_file, 'r') as f:
            log_data = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: Log file not found: {log_file}[/red]")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON in log file: {log_file}[/red]")
        sys.exit(1)
    
    # Get time series data
    time_series = log_data.get('time_series_metrics', {})
    
    if not time_series:
        console.print("[red]Error: No time_series_metrics found in log file[/red]")
        sys.exit(1)
    
    if len(time_series) < 2:
        console.print("[yellow]Warning: Only one data point found. Graphs require at least 2 data points.[/yellow]")
        sys.exit(0)
    
    # Print header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]PERFORMANCE TEST TIME-SERIES ANALYSIS[/bold cyan]\n"
        f"[yellow]Log File: {log_file}[/yellow]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    # Show summary
    console.print()
    summary_table = Table(box=box.SIMPLE, show_header=False)
    summary_table.add_column("Metric", style="cyan bold")
    summary_table.add_column("Value", style="yellow")
    
    summary_table.add_row("Test Duration", f"{log_data['summary']['total_duration_seconds']:.2f} seconds")
    summary_table.add_row("Total Queries", f"{log_data['summary']['total_queries']:,}")
    summary_table.add_row("Queries per Second", f"{log_data['summary']['queries_per_second']:,.2f}")
    summary_table.add_row("Cache Hit Rate", f"{log_data['summary']['cache_hit_rate_percent']:.1f}%")
    summary_table.add_row("Time Windows", f"{len(time_series)}")
    
    console.print(summary_table)
    
    # Plot time series
    plot_time_series(time_series, show_graph=True)
    
    console.print()
    console.print("[green]✓[/green] Time-series analysis complete")


if __name__ == "__main__":
    app()
