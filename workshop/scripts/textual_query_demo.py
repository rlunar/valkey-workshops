#!/usr/bin/env python3
"""
Textual-based Interactive Query Demo for Flughafen DB

This demo showcases different query complexity levels from simple table queries
to complex multi-table joins, following the flight rules for tier cities and routes.
Each query shows the SQL behind the scenes and includes EXPLAIN analysis.

Features:
- Interactive TUI with query selection
- Real-time SQL display
- Query execution with timing
- EXPLAIN plan analysis
- Flight rules implementation (ATL to JFK example)
- Progressive complexity from simple to advanced queries

Usage:
    python scripts/textual_query_demo.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Button, Static, Tree, DataTable, 
    TextArea, Tabs, TabPane, Label, ProgressBar
)
from textual.reactive import reactive
from textual.message import Message
from textual import on
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich.panel import Panel

import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from sqlmodel import Session, select, text, func, and_, or_
    from models.database import DatabaseManager
    from models.airport import Airport
    from models.airport_geo import AirportGeo
    from models.airline import Airline
    from models.flight import Flight
    from models.city import City, CityAirportRelation
    from models.country import Country
    from models.route import Route
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False


@dataclass
class QueryResult:
    """Container for query execution results"""
    sql: str
    execution_time: float
    row_count: int
    data: List[Dict[str, Any]]
    explain_plan: Optional[str] = None
    error: Optional[str] = None


class QueryDemo:
    """Query demonstration logic separated from UI"""
    
    def __init__(self):
        self.db_manager = None
        self.queries = self._define_queries()
    
    def connect_database(self) -> bool:
        """Connect to database and return success status"""
        try:
            self.db_manager = DatabaseManager()
            return True
        except Exception as e:
            return False
    
    def _define_queries(self) -> Dict[str, Dict[str, Any]]:
        """Define all demo queries with metadata"""
        return {
            "simple_airports": {
                "title": "Simple Table Query - Airports",
                "description": "Basic SELECT from airports table with IATA codes",
                "complexity": "Beginner",
                "sql_template": """
                SELECT 
                    airport_id,
                    name,
                    iata,
                    icao,
                    airport_type
                FROM airport 
                WHERE iata IS NOT NULL 
                ORDER BY name 
                LIMIT 10
                """,
                "category": "basic"
            },
            
            "tier1_airports": {
                "title": "Tier 1 Hub Airports (Flight Rules)",
                "description": "Major hub airports with 500+ routes (ATL, ORD, PEK, LHR, etc.)",
                "complexity": "Intermediate",
                "sql_template": """
                SELECT 
                    a.name,
                    a.iata,
                    a.icao,
                    ag.city,
                    ag.country,
                    COUNT(r.route_id) as route_count
                FROM airport a
                JOIN airport_geo ag ON a.airport_id = ag.airport_id
                LEFT JOIN route r ON a.openflights_id = r.source_airport_id_openflights 
                    OR a.openflights_id = r.destination_airport_id_openflights
                WHERE a.iata IN ('ATL', 'ORD', 'PEK', 'LHR', 'CDG', 'FRA', 'LAX', 'DFW', 'JFK', 'AMS')
                GROUP BY a.airport_id, a.name, a.iata, a.icao, ag.city, ag.country
                ORDER BY route_count DESC
                """,
                "category": "flight_rules"
            },
            
            "city_airport_join": {
                "title": "City-Airport Relationships",
                "description": "Join cities with their primary airports using geographic data",
                "complexity": "Intermediate", 
                "sql_template": """
                SELECT 
                    c.name as city_name,
                    c.country_code,
                    c.population,
                    a.name as airport_name,
                    a.iata,
                    car.distance_km,
                    car.is_primary_airport
                FROM city c
                JOIN city_airport_relation car ON c.city_id = car.city_id
                JOIN airport a ON car.airport_id = a.airport_id
                WHERE car.is_primary_airport = true
                    AND c.population > 1000000
                ORDER BY c.population DESC
                LIMIT 15
                """,
                "category": "joins"
            },
            
            "atl_to_jfk_routes": {
                "title": "ATL to JFK Route Analysis (Flight Rules Example)",
                "description": "Tier 1 to Tier 1 route analysis with airline and aircraft data",
                "complexity": "Advanced",
                "sql_template": """
                SELECT 
                    f.flightno,
                    al.name as airline_name,
                    al.iata as airline_code,
                    dep_a.name as departure_airport,
                    arr_a.name as arrival_airport,
                    f.departure,
                    f.arrival,
                    TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as flight_duration_minutes
                FROM flight f
                JOIN airport dep_a ON f.from_airport = dep_a.airport_id
                JOIN airport arr_a ON f.to_airport = arr_a.airport_id  
                JOIN airline al ON f.airline_id = al.airline_id
                WHERE dep_a.iata = 'ATL' 
                    AND arr_a.iata = 'JFK'
                ORDER BY f.departure DESC
                LIMIT 10
                """,
                "category": "flight_rules"
            },
            
            "complex_route_analysis": {
                "title": "Complex Multi-Table Route Analysis",
                "description": "Full route analysis with geographic, airline, and city data",
                "complexity": "Expert",
                "sql_template": """
                SELECT 
                    dep_city.name as departure_city,
                    dep_city.population as dep_population,
                    dep_ag.country as dep_country,
                    arr_city.name as arrival_city, 
                    arr_city.population as arr_population,
                    arr_ag.country as arr_country,
                    al.name as airline_name,
                    COUNT(f.flight_id) as flight_count,
                    AVG(TIMESTAMPDIFF(MINUTE, f.departure, f.arrival)) as avg_duration_minutes,
                    CASE 
                        WHEN COUNT(f.flight_id) >= 500 THEN 'Tier 1'
                        WHEN COUNT(f.flight_id) >= 200 THEN 'Tier 2' 
                        WHEN COUNT(f.flight_id) >= 50 THEN 'Tier 3'
                        ELSE 'Tier 4+'
                    END as route_tier
                FROM flight f
                JOIN airport dep_a ON f.from_airport = dep_a.airport_id
                JOIN airport arr_a ON f.to_airport = arr_a.airport_id
                JOIN airport_geo dep_ag ON dep_a.airport_id = dep_ag.airport_id
                JOIN airport_geo arr_ag ON arr_a.airport_id = arr_ag.airport_id
                JOIN airline al ON f.airline_id = al.airline_id
                LEFT JOIN city_airport_relation dep_car ON dep_a.airport_id = dep_car.airport_id AND dep_car.is_primary_airport = true
                LEFT JOIN city dep_city ON dep_car.city_id = dep_city.city_id
                LEFT JOIN city_airport_relation arr_car ON arr_a.airport_id = arr_car.airport_id AND arr_car.is_primary_airport = true  
                LEFT JOIN city arr_city ON arr_car.city_id = arr_city.city_id
                WHERE dep_ag.country != arr_ag.country
                GROUP BY 
                    dep_city.name, dep_city.population, dep_ag.country,
                    arr_city.name, arr_city.population, arr_ag.country, 
                    al.name
                HAVING flight_count >= 10
                ORDER BY flight_count DESC, avg_duration_minutes ASC
                LIMIT 20
                """,
                "category": "advanced"
            },
            
            "flight_frequency_analysis": {
                "title": "Flight Frequency by Distance (Flight Rules)",
                "description": "Analyze flight frequency recommendations based on distance tiers",
                "complexity": "Expert",
                "sql_template": """
                SELECT 
                    CASE 
                        WHEN 6371 * 2 * ASIN(SQRT(
                            POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
                            COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
                            POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
                        )) <= 1500 THEN 'Short-haul (0-1,500km)'
                        WHEN 6371 * 2 * ASIN(SQRT(
                            POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
                            COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
                            POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
                        )) <= 4000 THEN 'Medium-haul (1,500-4,000km)'
                        ELSE 'Long-haul (4,000+km)'
                    END as distance_category,
                    COUNT(DISTINCT CONCAT(dep_a.iata, '-', arr_a.iata)) as unique_routes,
                    COUNT(f.flight_id) as total_flights,
                    AVG(COUNT(f.flight_id)) OVER (PARTITION BY 
                        CASE 
                            WHEN 6371 * 2 * ASIN(SQRT(
                                POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
                                COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
                                POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
                            )) <= 1500 THEN 'Short-haul'
                            WHEN 6371 * 2 * ASIN(SQRT(
                                POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
                                COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
                                POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
                            )) <= 4000 THEN 'Medium-haul'
                            ELSE 'Long-haul'
                        END
                    ) as avg_flights_per_route
                FROM flight f
                JOIN airport dep_a ON f.from_airport = dep_a.airport_id
                JOIN airport arr_a ON f.to_airport = arr_a.airport_id
                JOIN airport_geo dep_ag ON dep_a.airport_id = dep_ag.airport_id
                JOIN airport_geo arr_ag ON arr_a.airport_id = arr_ag.airport_id
                WHERE dep_ag.latitude IS NOT NULL 
                    AND dep_ag.longitude IS NOT NULL
                    AND arr_ag.latitude IS NOT NULL 
                    AND arr_ag.longitude IS NOT NULL
                GROUP BY distance_category
                ORDER BY 
                    CASE distance_category
                        WHEN 'Short-haul (0-1,500km)' THEN 1
                        WHEN 'Medium-haul (1,500-4,000km)' THEN 2
                        ELSE 3
                    END
                """,
                "category": "flight_rules"
            }
        }
    
    def execute_query(self, query_key: str) -> QueryResult:
        """Execute a query and return results with timing and explain plan"""
        if not self.db_manager:
            return QueryResult(
                sql="", execution_time=0, row_count=0, data=[],
                error="Database not connected"
            )
        
        query_info = self.queries.get(query_key)
        if not query_info:
            return QueryResult(
                sql="", execution_time=0, row_count=0, data=[],
                error=f"Query '{query_key}' not found"
            )
        
        sql = query_info["sql_template"].strip()
        
        try:
            with Session(self.db_manager.engine) as session:
                # Execute EXPLAIN first
                explain_plan = None
                try:
                    # Use raw SQL for EXPLAIN - works with both MySQL and PostgreSQL
                    explain_sql = f"EXPLAIN {sql}"
                    explain_result = session.exec(text(explain_sql)).all()
                    
                    # Format explain results based on database type
                    if explain_result:
                        if hasattr(explain_result[0], '_fields'):
                            # Handle named tuple results
                            explain_lines = []
                            for row in explain_result:
                                if hasattr(row, '_fields'):
                                    explain_lines.append(" | ".join([str(getattr(row, field)) for field in row._fields]))
                                else:
                                    explain_lines.append(str(row))
                            explain_plan = "\n".join(explain_lines)
                        else:
                            # Handle other result types
                            explain_plan = "\n".join([str(row) for row in explain_result])
                    else:
                        explain_plan = "No execution plan returned"
                        
                except Exception as e:
                    explain_plan = f"EXPLAIN not available: {str(e)}"
                
                # Execute the actual query with timing
                start_time = time.time()
                result = session.exec(text(sql)).all()
                execution_time = time.time() - start_time
                
                # Convert results to list of dictionaries
                data = []
                if result:
                    # Get column names from the first row
                    first_row = result[0]
                    if hasattr(first_row, '_fields'):
                        # Named tuple result
                        columns = first_row._fields
                        data = [dict(zip(columns, row)) for row in result]
                    elif hasattr(first_row, 'keys'):
                        # Row result with keys
                        data = [dict(row) for row in result]
                    else:
                        # Fallback for other result types
                        data = [{"result": str(row)} for row in result]
                
                return QueryResult(
                    sql=sql,
                    execution_time=execution_time,
                    row_count=len(result),
                    data=data,
                    explain_plan=explain_plan
                )
                
        except Exception as e:
            return QueryResult(
                sql=sql, execution_time=0, row_count=0, data=[],
                error=str(e)
            )


class QueryDemoApp(App):
    """Main Textual application for the query demo"""
    
    CSS = """
    .query-list {
        width: 30%;
        border: solid $primary;
    }
    
    .main-content {
        width: 70%;
    }
    
    .sql-display {
        height: 40%;
        border: solid $secondary;
    }
    
    .results-display {
        height: 60%;
        border: solid $accent;
    }
    
    .status-bar {
        height: 3;
        background: $surface;
    }
    
    .query-button {
        width: 100%;
        margin: 1 0;
    }
    
    .complexity-beginner {
        color: $success;
    }
    
    .complexity-intermediate {
        color: $warning;
    }
    
    .complexity-advanced {
        color: $error;
    }
    
    .complexity-expert {
        color: $error;
        text-style: bold;
    }
    """
    
    TITLE = "Flughafen DB - Interactive Query Demo"
    SUB_TITLE = "From Simple Queries to Complex Flight Rules Analysis"
    
    current_query = reactive("")
    
    def __init__(self):
        super().__init__()
        self.demo = QueryDemo()
        self.current_result: Optional[QueryResult] = None
    
    def compose(self) -> ComposeResult:
        """Create the application layout"""
        yield Header()
        
        with Horizontal():
            # Left panel - Query selection
            with Vertical(classes="query-list"):
                yield Label("📋 Available Queries", classes="query-list-header")
                with ScrollableContainer():
                    yield from self._create_query_buttons()
            
            # Right panel - Main content
            with Vertical(classes="main-content"):
                with Tabs("sql", "results", "explain"):
                    with TabPane("SQL Query", id="sql"):
                        yield TextArea(
                            "Select a query from the left panel to see the SQL",
                            language="sql",
                            theme="monokai",
                            id="sql-display",
                            classes="sql-display"
                        )
                    
                    with TabPane("Query Results", id="results"):
                        yield DataTable(id="results-table", classes="results-display")
                    
                    with TabPane("Execution Plan", id="explain"):
                        yield TextArea(
                            "Query execution plan will appear here",
                            language="text",
                            theme="monokai", 
                            id="explain-display",
                            classes="sql-display"
                        )
        
        # Status bar
        with Container(classes="status-bar"):
            yield Label("🔌 Connecting to database...", id="status-label")
            yield ProgressBar(id="progress-bar", show_eta=False)
        
        yield Footer()
    
    def _create_query_buttons(self) -> ComposeResult:
        """Create query buttons for the scrollable container"""
        for query_key, query_info in self.demo.queries.items():
            complexity = query_info["complexity"]
            complexity_class = f"complexity-{complexity.lower()}"
            
            yield Button(
                f"{query_info['title']}\n[{complexity}]",
                id=f"query-{query_key}",
                classes=f"query-button {complexity_class}"
            )
    
    async def on_mount(self) -> None:
        """Initialize the application"""
        # Try to connect to database
        status_label = self.query_one("#status-label", Label)
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        
        progress_bar.update(progress=50)
        status_label.update("🔌 Connecting to database...")
        
        if self.demo.connect_database():
            status_label.update("✅ Database connected successfully")
            progress_bar.update(progress=100)
        else:
            status_label.update("❌ Database connection failed - Check .env configuration")
            progress_bar.update(progress=0)
    
    @on(Button.Pressed)
    async def handle_query_button(self, event: Button.Pressed) -> None:
        """Handle query button press"""
        if not event.button.id or not event.button.id.startswith("query-"):
            return
        
        query_key = event.button.id.replace("query-", "")
        await self.execute_query(query_key)
    
    async def execute_query(self, query_key: str) -> None:
        """Execute selected query and update displays"""
        status_label = self.query_one("#status-label", Label)
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        
        status_label.update(f"🔄 Executing query: {query_key}")
        progress_bar.update(progress=25)
        
        # Execute query
        result = self.demo.execute_query(query_key)
        self.current_result = result
        
        progress_bar.update(progress=75)
        
        # Update SQL display
        sql_display = self.query_one("#sql-display", TextArea)
        sql_display.text = result.sql
        
        # Update results table
        await self._update_results_table(result)
        
        # Update explain display
        explain_display = self.query_one("#explain-display", TextArea)
        explain_display.text = result.explain_plan or "No execution plan available"
        
        # Update status
        if result.error:
            status_label.update(f"❌ Query failed: {result.error}")
            progress_bar.update(progress=0)
        else:
            status_label.update(
                f"✅ Query executed: {result.row_count} rows in {result.execution_time:.3f}s"
            )
            progress_bar.update(progress=100)
    
    async def _update_results_table(self, result: QueryResult) -> None:
        """Update the results data table"""
        table = self.query_one("#results-table", DataTable)
        table.clear(columns=True)
        
        if result.error:
            table.add_column("Error", key="error")
            table.add_row(result.error)
            return
        
        if not result.data:
            table.add_column("Message", key="message")
            table.add_row("No results returned")
            return
        
        # Add columns based on first row
        first_row = result.data[0]
        for column_name in first_row.keys():
            table.add_column(str(column_name), key=str(column_name))
        
        # Add data rows
        for row_data in result.data:
            row_values = []
            for column_name in first_row.keys():
                value = row_data.get(column_name, "")
                # Format the value for display
                if isinstance(value, datetime):
                    row_values.append(value.strftime("%Y-%m-%d %H:%M"))
                elif isinstance(value, (int, float)) and value is not None:
                    row_values.append(f"{value:,}" if isinstance(value, int) else f"{value:.2f}")
                else:
                    row_values.append(str(value) if value is not None else "")
            
            table.add_row(*row_values)


def main():
    """Main entry point"""
    if not DEPENDENCIES_AVAILABLE:
        console = Console()
        console.print(Panel.fit(
            "[red]Dependencies not available![/red]\n\n"
            "Install with: [cyan]uv sync[/cyan]\n\n"
            "Required packages:\n"
            "• textual\n"
            "• sqlmodel\n" 
            "• rich\n"
            "• python-dotenv",
            title="❌ Missing Dependencies"
        ))
        return
    
    # Check for .env file
    if not os.path.exists('.env'):
        console = Console()
        console.print(Panel.fit(
            "[yellow]No .env file found![/yellow]\n\n"
            "Copy [cyan].env.example[/cyan] to [cyan].env[/cyan] and configure your database connection.\n\n"
            "Required environment variables:\n"
            "• DB_TYPE (mysql/postgresql)\n"
            "• DB_HOST\n"
            "• DB_NAME\n"
            "• DB_USER\n"
            "• DB_PASSWORD",
            title="⚠️  Configuration Required"
        ))
        return
    
    app = QueryDemoApp()
    app.run()


if __name__ == "__main__":
    main()