#!/usr/bin/env python3
"""
Test the enhanced knowledge base loading with more context
"""

from daos.nlp_to_sql import NLPToSQL
from rich.console import Console

console = Console()

console.print("\n[bold cyan]Testing Enhanced Knowledge Base Loading[/bold cyan]\n")
console.print("=" * 70)

# Initialize converter - this will show the enhanced context stats
try:
    converter = NLPToSQL(knowledge_base_path="knowledge_base")  # Uses OLLAMA_MODEL from .env
    
    console.print("\n[bold green]✅ Knowledge base loaded successfully![/bold green]")
    console.print("\n[bold]Context Preview (first 1000 chars):[/bold]")
    console.print("[dim]" + converter.context[:1000] + "...[/dim]")
    
    console.print("\n[bold]Tables included in context:[/bold]")
    tables = [
        'airport', 'airport_geo', 'airport_reachable',
        'flight', 'flightschedule', 'flight_log',
        'passenger', 'passengerdetails', 'booking',
        'airline', 'airplane', 'airplane_type',
        'employee', 'weatherdata'
    ]
    for table in tables:
        if table.upper() in converter.context:
            console.print(f"  ✓ {table}", style="green")
        else:
            console.print(f"  ✗ {table}", style="dim")
    
    console.print("\n[bold]Example query types included:[/bold]")
    query_types = [
        ('Simple Queries', 'query_examples_simple'),
        ('Join Queries', 'query_examples_joins'),
        ('Aggregation Queries', 'query_examples_aggregations'),
        ('Natural Language Examples', 'nl_sql_examples')
    ]
    for name, marker in query_types:
        if marker in converter.context or name in converter.context:
            console.print(f"  ✓ {name}", style="green")
        else:
            console.print(f"  ✗ {name}", style="dim")
    
except Exception as e:
    console.print(f"\n[bold red]❌ Error loading knowledge base:[/bold red] {e}")
    import traceback
    console.print(traceback.format_exc())

console.print("\n" + "=" * 70)
