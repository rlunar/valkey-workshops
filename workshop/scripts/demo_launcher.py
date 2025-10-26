#!/usr/bin/env python3
"""
Demo Launcher for Textual Query Demo

This script provides a simple way to launch the interactive query demo
with proper error handling and setup guidance.
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import textual
    except ImportError:
        missing_deps.append("textual")
    
    try:
        import sqlmodel
    except ImportError:
        missing_deps.append("sqlmodel")
    
    try:
        import rich
    except ImportError:
        missing_deps.append("rich")
    
    return missing_deps

def check_env_file():
    """Check if .env file exists and is configured"""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if not env_path.exists():
        return False, "missing"
    
    # Check if it's just a copy of the example
    if env_example_path.exists():
        try:
            with open(env_path) as f:
                env_content = f.read()
            with open(env_example_path) as f:
                example_content = f.read()
            
            if env_content.strip() == example_content.strip():
                return False, "unconfigured"
        except Exception:
            pass
    
    return True, "configured"

def show_setup_instructions(console: Console, missing_deps: list, env_status: tuple):
    """Show setup instructions based on what's missing"""
    
    if missing_deps:
        console.print(Panel.fit(
            f"[red]Missing Dependencies:[/red]\n\n"
            f"The following packages are required:\n"
            + "\n".join([f"• {dep}" for dep in missing_deps]) +
            f"\n\n[cyan]Install with:[/cyan]\n"
            f"uv sync\n\n"
            f"[yellow]Or manually:[/yellow]\n"
            f"pip install " + " ".join(missing_deps),
            title="❌ Setup Required"
        ))
        return False
    
    env_configured, env_reason = env_status
    if not env_configured:
        if env_reason == "missing":
            console.print(Panel.fit(
                "[yellow]Database Configuration Required[/yellow]\n\n"
                "Copy the example environment file and configure your database:\n\n"
                "[cyan]cp .env.example .env[/cyan]\n\n"
                "Then edit .env with your database credentials:\n"
                "• DB_TYPE (mysql/postgresql)\n"
                "• DB_HOST\n"
                "• DB_NAME\n"
                "• DB_USER\n"
                "• DB_PASSWORD",
                title="⚠️  Configuration Required"
            ))
        else:
            console.print(Panel.fit(
                "[yellow]Database Configuration Incomplete[/yellow]\n\n"
                "Your .env file appears to be unconfigured.\n"
                "Please edit .env with your actual database credentials:\n\n"
                "• Replace 'username' with your database user\n"
                "• Replace 'password' with your database password\n"
                "• Update host, port, and database name as needed",
                title="⚠️  Configuration Required"
            ))
        return False
    
    return True

def show_demo_info(console: Console):
    """Show information about the demo"""
    
    # Create a table of available queries
    table = Table(title="🎯 Available Demo Queries")
    table.add_column("Query", style="cyan", no_wrap=True)
    table.add_column("Complexity", style="bold")
    table.add_column("Description", style="dim")
    
    queries = [
        ("Simple Airports", "🟢 Beginner", "Basic SELECT from airports table"),
        ("Tier 1 Hubs", "🟡 Intermediate", "Major hub airports (ATL, ORD, JFK, etc.)"),
        ("City-Airport Join", "🟡 Intermediate", "Geographic relationships"),
        ("ATL to JFK Routes", "🔴 Advanced", "Tier 1 to Tier 1 route analysis"),
        ("Complex Analysis", "🔴 Expert", "Multi-table joins with flight rules"),
        ("Distance Analysis", "🔴 Expert", "Geographic calculations & frequency")
    ]
    
    for query, complexity, description in queries:
        table.add_row(query, complexity, description)
    
    console.print(table)
    console.print()
    
    # Show features
    features_text = Text()
    features_text.append("✨ Demo Features:\n", style="bold cyan")
    features_text.append("• Interactive TUI with query selection\n")
    features_text.append("• Real-time SQL display with syntax highlighting\n") 
    features_text.append("• Query execution timing and row counts\n")
    features_text.append("• EXPLAIN plan analysis for performance insights\n")
    features_text.append("• Flight rules implementation (aviation industry practices)\n")
    features_text.append("• Progressive complexity from beginner to expert level\n")
    
    console.print(Panel(features_text, title="🚀 Interactive Query Demo"))

def main():
    """Main launcher function"""
    console = Console()
    
    # Show header
    console.print()
    console.print("🛫 [bold cyan]Flughafen DB - Interactive Query Demo[/bold cyan]")
    console.print("[dim]From Simple Queries to Complex Flight Rules Analysis[/dim]")
    console.print()
    
    # Check dependencies
    missing_deps = check_dependencies()
    env_status = check_env_file()
    
    # Show setup instructions if needed
    if not show_setup_instructions(console, missing_deps, env_status):
        console.print("\n[dim]Run this script again after completing the setup.[/dim]")
        return
    
    # Show demo information
    show_demo_info(console)
    
    # Launch the demo
    console.print("\n[green]✅ All requirements met! Launching interactive demo...[/green]")
    console.print("[dim]Press Ctrl+C to exit the demo at any time.[/dim]\n")
    
    try:
        # Import and run the demo
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from textual_query_demo import QueryDemoApp
        
        app = QueryDemoApp()
        app.run()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error launching demo: {e}[/red]")
        console.print("[dim]Check your database configuration and try again.[/dim]")

if __name__ == "__main__":
    main()