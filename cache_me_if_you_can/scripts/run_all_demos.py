#!/usr/bin/env python3
"""
Run All Demos Script (Python version)

This script executes all demo scripts in the samples folder sequentially.
Uses Typer for CLI and Rich for beautiful terminal output.

Enhanced demos include:
- Cache-Aside: Rich tables, verbose mode, interactive prompts
- Write-Through: Consistency verification, detailed output
- Write-Behind: Async operations, queue monitoring
- Weather API: Country flags 🇺🇸, weather emojis ☀️, syntax-highlighted JSON
- Semantic Cache: Vector similarity for NLP queries, token savings, performance metrics
- Multi-threaded: Performance metrics, JSON output, visualization support

Usage:
    python scripts/run_all_demos.py              # Run all demos
    python scripts/run_all_demos.py --help       # Show help
    python scripts/run_all_demos.py --skip-prompts  # Run without pauses
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.prompt import Confirm

# Initialize typer app and rich console
app = typer.Typer(
    help="Run all cache pattern demonstrations sequentially",
    add_completion=False
)
console = Console()

# Get project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"


class DemoRunner:
    """Handles running demos and tracking results."""
    
    def __init__(
        self,
        skip_prompts: bool = False,
        interactive: bool = False,
        verbose: bool = False,
        flush: bool = False
    ):
        self.skip_prompts = skip_prompts
        self.interactive = interactive
        self.verbose = verbose
        self.flush = flush
        self.total_demos = 0
        self.successful_demos = 0
        self.failed_demos = 0
        self.results = []
    
    def run_demo(
        self,
        name: str,
        script: str,
        args: Optional[list] = None,
        description: Optional[str] = None,
        tip: Optional[str] = None,
        supports_interactive: bool = False,
        supports_verbose: bool = False,
        supports_flush: bool = False
    ) -> bool:
        """Run a single demo and track results."""
        self.total_demos += 1
        
        # Print demo header
        console.print()
        console.print(Panel(
            f"[bold cyan]{name}[/bold cyan]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        
        if description:
            console.print(f"[dim]{description}[/dim]")
        
        # Check if demo file exists
        demo_path = SAMPLES_DIR / script
        if not demo_path.exists():
            console.print(f"[red]✗ Demo file not found: {script}[/red]")
            self.failed_demos += 1
            self.results.append({"name": name, "status": "failed", "reason": "File not found"})
            return False
        
        # Build command
        cmd = ["uv", "run", str(demo_path)]
        if args:
            cmd.extend(args)
        
        # Add global flags if supported by the demo
        if self.interactive and supports_interactive:
            cmd.append("--interactive")
        if self.verbose and supports_verbose:
            cmd.append("--verbose")
        if self.flush and supports_flush:
            cmd.append("--flush")
        
        # Run demo with progress indicator
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"[cyan]Running {name}...", total=None)
                
                result = subprocess.run(
                    cmd,
                    cwd=PROJECT_ROOT,
                    capture_output=False,
                    text=True
                )
                
                progress.update(task, completed=True)
            
            if result.returncode == 0:
                console.print(f"[green]✓ {name} completed successfully[/green]")
                self.successful_demos += 1
                self.results.append({"name": name, "status": "success"})
                
                # Show tip if provided
                if tip:
                    console.print(f"[blue]💡 Tip:[/blue] [dim]{tip}[/dim]")
                
                return True
            else:
                console.print(f"[red]✗ {name} failed with exit code {result.returncode}[/red]")
                self.failed_demos += 1
                self.results.append({"name": name, "status": "failed", "reason": f"Exit code {result.returncode}"})
                return False
                
        except Exception as e:
            console.print(f"[red]✗ {name} failed with error: {e}[/red]")
            self.failed_demos += 1
            self.results.append({"name": name, "status": "failed", "reason": str(e)})
            return False
    
    def prompt_continue(self):
        """Prompt user to continue to next demo."""
        if not self.skip_prompts:
            console.print()
            if not Confirm.ask("[dim]Continue to next demo?[/dim]", default=True):
                console.print("[yellow]⚠ Demo execution stopped by user[/yellow]")
                sys.exit(0)
    
    def print_summary(self):
        """Print execution summary."""
        console.print()
        console.print(Panel(
            "[bold cyan]Demo Execution Summary[/bold cyan]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        
        # Create summary table
        summary_table = Table(box=box.ROUNDED, show_header=False)
        summary_table.add_column("Metric", style="cyan bold")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Total demos run", str(self.total_demos))
        summary_table.add_row("Successful", f"[green]{self.successful_demos} ✓[/green]")
        
        if self.failed_demos > 0:
            summary_table.add_row("Failed", f"[red]{self.failed_demos} ✗[/red]")
        else:
            summary_table.add_row("Failed", str(self.failed_demos))
        
        console.print(summary_table)
        
        # Show detailed results if there were failures
        if self.failed_demos > 0:
            console.print()
            results_table = Table(title="Detailed Results", box=box.ROUNDED)
            results_table.add_column("Demo", style="cyan")
            results_table.add_column("Status", style="white")
            results_table.add_column("Details", style="dim")
            
            for result in self.results:
                status_icon = "✓" if result["status"] == "success" else "✗"
                status_color = "green" if result["status"] == "success" else "red"
                status_text = f"[{status_color}]{status_icon} {result['status'].upper()}[/{status_color}]"
                details = result.get("reason", "")
                
                results_table.add_row(result["name"], status_text, details)
            
            console.print(results_table)
        
        # Final message
        console.print()
        if self.failed_demos == 0:
            console.print(Panel(
                "[bold green]✓ All demos completed successfully![/bold green]\n\n"
                "[cyan]Next steps:[/cyan]\n"
                "  • Try demos with [yellow]--verbose[/yellow] flag for detailed output\n"
                "  • Use [yellow]--interactive[/yellow] mode to step through each phase\n"
                "  • Check [yellow]logs/[/yellow] directory for performance test results\n"
                "  • Run [yellow]python scripts/run_all_demos.py --help[/yellow] for options",
                border_style="green",
                box=box.DOUBLE
            ))
        else:
            console.print(Panel(
                "[bold yellow]⚠ Some demos failed[/bold yellow]\n\n"
                "[cyan]Troubleshooting:[/cyan]\n"
                "  • Check that Valkey/Redis is running\n"
                "  • Verify .env configuration\n"
                "  • Review error messages above\n"
                "  • Try running failed demos individually",
                border_style="yellow",
                box=box.DOUBLE
            ))


@app.command()
def main(
    skip_prompts: bool = typer.Option(
        False,
        "--skip-prompts",
        "-y",
        help="Run all demos without pausing between them"
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Run demos in interactive mode (step-by-step with prompts)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show verbose output with detailed information"
    ),
    flush: bool = typer.Option(
        False,
        "--flush",
        "-f",
        help="Flush cache before running demos"
    )
):
    """
    Run all cache pattern demonstrations sequentially.
    
    This script runs the following demos:
    
    1. Cache-Aside Pattern - Read-through caching with lazy loading
    
    2. Write-Through Cache - Synchronous write to DB and cache
    
    3. Write-Behind Cache - Asynchronous write with queue
    
    4. Weather API Cache - Real-world API caching with emojis
    
    5. Semantic Cache - Vector similarity caching for NLP to SQL queries
    
    6. Stampede Prevention - Distributed locking for cache stampede
    
    7. Multi-threaded Performance - Concurrent load testing
    
    Enhanced features include:
    
    • Rich terminal formatting with colors and tables
    
    • Country flags 🇺🇸 🇲🇽 🇬🇧 and weather emojis ☀️ 🌧️ ⛅
    
    • Syntax-highlighted JSON output
    
    • Interactive and verbose modes
    
    • Performance metrics and visualizations
    
    Examples:
    
        # Run all demos interactively
        python scripts/run_all_demos.py
        
        # Skip prompts (non-interactive)
        python scripts/run_all_demos.py --skip-prompts
        
        # Run with verbose output
        python scripts/run_all_demos.py --verbose
        
        # Run in interactive mode with verbose output
        python scripts/run_all_demos.py --interactive --verbose
        
        # Flush cache before running demos
        python scripts/run_all_demos.py --flush
        
        # Combine all flags
        python scripts/run_all_demos.py --skip-prompts --verbose --flush
        
        # Individual demos
        uv run samples/demo_weather_api_cache.py -v -c 5
        uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000
    """
    
    # Print header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Running All Cache Pattern Demos[/bold cyan]\n"
        "[yellow]Enhanced with Rich formatting, emojis, and interactive modes[/yellow]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    # Check .env file
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        console.print()
        console.print(Panel(
            "[bold red]✗ Error: .env file not found[/bold red]\n\n"
            "Please copy .env.example to .env and configure it:\n"
            "  [yellow]cp .env.example .env[/yellow]",
            border_style="red",
            box=box.ROUNDED
        ))
        sys.exit(1)
    
    # Show flags status if any are enabled
    if interactive or verbose or flush:
        console.print()
        flags_table = Table(title="Enabled Flags", box=box.ROUNDED, show_header=False)
        flags_table.add_column("Flag", style="cyan bold")
        flags_table.add_column("Status", style="white")
        
        if interactive:
            flags_table.add_row("Interactive", "[green]✓ Enabled[/green]")
        if verbose:
            flags_table.add_row("Verbose", "[green]✓ Enabled[/green]")
        if flush:
            flags_table.add_row("Flush Cache", "[green]✓ Enabled[/green]")
        
        console.print(flags_table)
    
    # Initialize runner
    runner = DemoRunner(
        skip_prompts=skip_prompts,
        interactive=interactive,
        verbose=verbose,
        flush=flush
    )
    
    # Demo 1: Cache-Aside Pattern
    runner.run_demo(
        name="Cache-Aside Pattern Demo",
        script="demo_cache_aside.py",
        description="Demonstrates read-through caching with lazy loading",
        tip="Try with --interactive and --verbose flags for detailed output",
        supports_interactive=True,
        supports_verbose=True,
        supports_flush=False
    )
    runner.prompt_continue()
    
    # Demo 2: Write-Through Cache Pattern
    runner.run_demo(
        name="Write-Through Cache Pattern Demo",
        script="demo_write_through_cache.py",
        description="Shows synchronous writes to both database and cache",
        tip="Watch for consistency verification between DB and cache",
        supports_interactive=True,
        supports_verbose=True,
        supports_flush=False
    )
    runner.prompt_continue()
    
    # Demo 3: Write-Behind Cache Pattern
    runner.run_demo(
        name="Write-Behind Cache Pattern Demo",
        script="demo_write_behind_cache.py",
        description="Demonstrates asynchronous writes with queue processing",
        tip="Observe the queue monitoring and batch processing",
        supports_interactive=True,
        supports_verbose=True,
        supports_flush=False
    )
    runner.prompt_continue()
    
    # Demo 4: Weather API Cache
    runner.run_demo(
        name="Weather API Cache Demo",
        script="demo_weather_api_cache.py",
        args=["--cities", "5", "--ttl", "15"],
        description="Real-world API caching with country flags 🇺🇸 🇲🇽 🇬🇧 and weather emojis ☀️ 🌧️ ⛅",
        tip="Run with --verbose to see cache keys and syntax-highlighted JSON samples",
        supports_interactive=True,
        supports_verbose=True,
        supports_flush=True
    )
    runner.prompt_continue()
    
    # Demo 5: Semantic Cache
    runner.run_demo(
        name="Semantic Cache Pattern Demo",
        script="demo_semantic_cache.py",
        description="Vector similarity caching for natural language SQL queries with embeddings",
        tip="Watch for semantic cache hits on similar queries - saves LLM tokens and latency",
        supports_interactive=True,
        supports_verbose=True,
        supports_flush=True
    )
    runner.prompt_continue()
    
    # Demo 6: Stampede Prevention
    runner.run_demo(
        name="Stampede Prevention Demo",
        script="demo_stampede_prevention.py",
        args=["--requests", "1000", "--threads", "4", "--cities", "3"],
        description="Distributed locking to prevent cache stampede with concurrent requests",
        tip="Watch how only 1 API call is made despite 1000 concurrent requests per city",
        supports_interactive=True,
        supports_verbose=True,
        supports_flush=True
    )
    runner.prompt_continue()
    
    # Demo 7: Multi-threaded Performance Test
    runner.run_demo(
        name="Multi-threaded Performance Test",
        script="demo_multi_threaded_performance.py",
        args=["--threads", "4", "--queries", "1000"],
        description="Tests cache performance under concurrent load (4 threads, 1000 queries each)",
        tip="Results saved to logs/ directory. View with: uv run samples/plot_time_series.py logs/perf_test_*.json",
        supports_interactive=False,
        supports_verbose=False,
        supports_flush=False
    )
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if runner.failed_demos == 0 else 1)


if __name__ == "__main__":
    app()
