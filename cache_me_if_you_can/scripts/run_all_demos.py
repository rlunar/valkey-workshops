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
CORE_DIR = PROJECT_ROOT / "core"
DAOS_DIR = PROJECT_ROOT / "daos"


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
    
    def discover_scripts(self) -> list[dict]:
        """Discover all runnable Python scripts in core, daos, and samples folders."""
        scripts = []
        
        # Scripts to exclude (utilities, not demos)
        exclude_scripts = {"plot_time_series.py"}
        
        # Discover scripts in each folder
        for folder_name, folder_path in [
            ("core", CORE_DIR),
            ("daos", DAOS_DIR),
            ("samples", SAMPLES_DIR)
        ]:
            if not folder_path.exists():
                continue
            
            # Find all .py files excluding __init__.py and __pycache__
            for script_path in sorted(folder_path.glob("*.py")):
                if script_path.name.startswith("__") or script_path.name in exclude_scripts:
                    continue
                
                # Determine if it's a demo or module
                is_demo = script_path.name.startswith("demo_") or folder_name == "samples"
                
                scripts.append({
                    "name": script_path.stem.replace("_", " ").title(),
                    "path": script_path,
                    "folder": folder_name,
                    "is_demo": is_demo,
                    "relative_path": script_path.relative_to(PROJECT_ROOT)
                })
        
        return scripts
    
    def run_script(
        self,
        script_info: dict,
        args: Optional[list] = None
    ) -> bool:
        """Run a single script and track results."""
        self.total_demos += 1
        
        name = script_info["name"]
        script_path = script_info["path"]
        folder = script_info["folder"]
        
        # Print script header
        console.print()
        console.print(Panel(
            f"[bold cyan]{name}[/bold cyan]\n"
            f"[dim]{folder}/{script_path.name}[/dim]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        
        # Check if script file exists
        if not script_path.exists():
            console.print(f"[red]✗ Script file not found: {script_path}[/red]")
            self.failed_demos += 1
            self.results.append({"name": name, "status": "failed", "reason": "File not found"})
            return False
        
        # Build command
        cmd = ["uv", "run", str(script_path)]
        if args:
            cmd.extend(args)
        
        # Add global flags for demo scripts
        if script_info["is_demo"]:
            if self.interactive and "--interactive" not in cmd:
                cmd.append("--interactive")
            if self.verbose and "--verbose" not in cmd:
                cmd.append("--verbose")
            if self.flush and "--flush" not in cmd:
                cmd.append("--flush")
        
        # Run script with progress indicator
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
    
    def plot_latest_performance_log(self):
        """Find and plot the latest performance test log file."""
        logs_dir = PROJECT_ROOT / "logs"
        
        if not logs_dir.exists():
            console.print("[dim]No logs directory found, skipping visualization[/dim]")
            return
        
        # Find the most recent perf_test_*.json file
        log_files = sorted(logs_dir.glob("perf_test_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if not log_files:
            console.print("[dim]No performance test logs found, skipping visualization[/dim]")
            return
        
        latest_log = log_files[0]
        
        console.print()
        console.print(Panel(
            f"[bold cyan]Visualizing Performance Results[/bold cyan]\n"
            f"[dim]Log file: {latest_log.name}[/dim]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        
        # Run plot_time_series.py with plot-only command
        plot_script = SAMPLES_DIR / "plot_time_series.py"
        cmd = ["uv", "run", str(plot_script), "plot-only", str(latest_log)]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Performance visualization completed[/green]")
            else:
                console.print(f"[yellow]⚠ Visualization failed with exit code {result.returncode}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not visualize results: {e}[/yellow]")
    
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
        help="Run all scripts without pausing between them"
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
    ),
    list_scripts: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all discovered scripts and exit"
    )
):
    """
    Run all Python scripts in core, daos, and samples folders sequentially.
    
    This script automatically discovers and runs all Python scripts in:
    
    • core/ - Core functionality modules
    
    • daos/ - Data Access Object implementations
    
    • samples/ - Demo and example scripts
    
    Enhanced features include:
    
    • Automatic script discovery
    
    • Rich terminal formatting with colors and tables
    
    • Country flags 🇺🇸 🇲🇽 🇬🇧 and weather emojis ☀️ 🌧️ ⛅
    
    • Syntax-highlighted JSON output
    
    • Interactive and verbose modes
    
    • Performance metrics and visualizations
    
    Examples:
    
        # List all discovered scripts
        python scripts/run_all_demos.py --list
        
        # Run all scripts interactively
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
    """
    
    # Initialize runner
    runner = DemoRunner(
        skip_prompts=skip_prompts,
        interactive=interactive,
        verbose=verbose,
        flush=flush
    )
    
    # Discover all scripts
    scripts = runner.discover_scripts()
    
    if not scripts:
        console.print()
        console.print(Panel(
            "[bold red]✗ Error: No scripts found[/bold red]\n\n"
            "No Python scripts were discovered in core/, daos/, or samples/ folders.",
            border_style="red",
            box=box.ROUNDED
        ))
        sys.exit(1)
    
    # If --list flag, show scripts and exit
    if list_scripts:
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Discovered Scripts[/bold cyan]",
            border_style="cyan",
            box=box.DOUBLE
        ))
        
        scripts_table = Table(box=box.ROUNDED)
        scripts_table.add_column("#", style="dim", width=4)
        scripts_table.add_column("Folder", style="cyan")
        scripts_table.add_column("Script", style="white")
        scripts_table.add_column("Type", style="yellow")
        
        for idx, script in enumerate(scripts, 1):
            script_type = "Demo" if script["is_demo"] else "Module"
            scripts_table.add_row(
                str(idx),
                script["folder"],
                script["path"].name,
                script_type
            )
        
        console.print(scripts_table)
        console.print(f"\n[cyan]Total scripts found:[/cyan] {len(scripts)}")
        sys.exit(0)
    
    # Print header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Running All Scripts[/bold cyan]\n"
        f"[yellow]Found {len(scripts)} scripts in core/, daos/, and samples/ folders[/yellow]",
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
    
    # Run all discovered scripts
    for idx, script in enumerate(scripts, 1):
        console.print(f"\n[dim]Script {idx} of {len(scripts)}[/dim]")
        
        # Add specific args for certain demos
        args = None
        if script["path"].name == "demo_weather_api_cache.py":
            args = ["--cities", "5", "--ttl", "15"]
        elif script["path"].name == "demo_stampede_prevention.py":
            args = ["--requests", "1000", "--threads", "4", "--cities", "3"]
        elif script["path"].name == "demo_multi_threaded_performance.py":
            args = ["--threads", "4", "--queries", "1000"]
        
        success = runner.run_script(script, args=args)
        
        # After multi-threaded performance test, visualize the results
        if success and script["path"].name == "demo_multi_threaded_performance.py":
            runner.plot_latest_performance_log()
        
        # Prompt to continue if not last script
        if idx < len(scripts):
            runner.prompt_continue()
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if runner.failed_demos == 0 else 1)


if __name__ == "__main__":
    app()
