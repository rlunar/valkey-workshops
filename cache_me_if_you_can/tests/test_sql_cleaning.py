#!/usr/bin/env python3
"""
Test the improved SQL cleaning that separates SQL from explanations
"""

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
import sqlparse

console = Console()

def clean_sql(sql: str) -> str:
    """Clean up generated SQL query and separate from explanations"""
    # Remove markdown code blocks if present
    sql = sql.replace("```sql", "").replace("```", "")
    
    # Remove common prefixes
    prefixes = ["SQL Query:", "Query:", "SQL:"]
    for prefix in prefixes:
        if sql.startswith(prefix):
            sql = sql[len(prefix):].strip()
    
    # Split by lines and find where SQL ends
    lines = sql.split('\n')
    sql_lines = []
    found_semicolon = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines at the start
        if not sql_lines and not line_stripped:
            continue
        
        # If we found a semicolon and hit a non-empty line, it's likely an explanation
        if found_semicolon and line_stripped:
            # Check if this looks like SQL continuation (unlikely after semicolon)
            # or an explanation
            line_lower = line_stripped.lower()
            
            # Common explanation patterns
            explanation_patterns = [
                'this sql', 'this query', 'the sql', 'the query', 'the above',
                'note:', 'explanation:', 'this will', 'this returns',
                'here', 'above query', 'in this example', 'in the example',
                'we are using', 'we use', 'the resulting'
            ]
            
            if any(line_lower.startswith(pattern) for pattern in explanation_patterns):
                break
        
        # Check if this line looks like an explanation (not SQL)
        line_lower = line_stripped.lower()
        explanation_starters = [
            'this sql', 'this query', 'the sql', 'the query',
            'note:', 'explanation:', 'this will', 'this returns',
            'here', 'above', 'below', 'in this example', 'in the example',
            'we are using', 'we use', 'the resulting'
        ]
        
        is_explanation = any(
            line_lower.startswith(starter) 
            for starter in explanation_starters
        )
        
        # If we've started collecting SQL and hit an explanation, stop
        if sql_lines and is_explanation:
            break
        
        # Check if line has SQL keywords at the start (more strict)
        sql_start_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 
                              'OUTER', 'LIMIT', 'ORDER', 'GROUP', 'HAVING', 'INSERT', 
                              'UPDATE', 'DELETE', 'WITH', 'UNION', 'AND', 'OR', 'ON']
        
        # For lines after we've started collecting, be more lenient
        if sql_lines:
            # If it's not an explanation and not empty, include it
            if line_stripped and not is_explanation:
                sql_lines.append(line)
                if ';' in line:
                    found_semicolon = True
            elif not line_stripped:
                # Empty line - include if we haven't hit semicolon yet
                if not found_semicolon:
                    sql_lines.append(line)
        else:
            # First line - must start with a SQL keyword
            first_word = line_stripped.split()[0].upper() if line_stripped.split() else ""
            if first_word in sql_start_keywords:
                sql_lines.append(line)
    
    # Join the SQL lines back together
    sql = '\n'.join(sql_lines).strip()
    
    # Remove trailing semicolon if present
    sql = sql.rstrip(";").strip()
    
    # If we ended up with nothing, return the original (fallback)
    if not sql:
        sql = lines[0] if lines else ""
    
    return sql

def pretty_print_sql(sql: str, title: str = "SQL"):
    """Pretty print SQL with syntax highlighting"""
    formatted = sqlparse.format(sql, reindent=True, keyword_case='upper', indent_width=2)
    syntax = Syntax(formatted, "sql", theme="monokai", line_numbers=True, word_wrap=True)
    console.print(Panel(syntax, title=title, border_style="cyan"))

# Test cases with SQL + explanations (like your example)
test_cases = [
    {
        "name": "SQL with explanation after",
        "raw": """SELECT *
FROM `flughafen.flughafen_airport`
WHERE IATA = 'JFK'
LIMIT 1;

This SQL query will RETURN the airport WITH geographic details BY IATA code "JFK"
FROM the Flughafen airport DATABASE TABLE named "flughafen_airport". The
LIMIT clause limits the number OF ROWS returned TO one."""
    },
    {
        "name": "SQL with 'This query' explanation",
        "raw": """SELECT airport_id, name, country
FROM airport
WHERE country = 'USA'
LIMIT 10;

This query retrieves the first 10 airports in the USA."""
    },
    {
        "name": "SQL with 'Note:' explanation",
        "raw": """SELECT f.flight_id, f.departure, f.arrival
FROM flight f
JOIN airport a ON f.from_airport = a.airport_id
WHERE a.iata_code = 'LAX'
LIMIT 20;

Note: This uses a JOIN to connect flights with airports."""
    },
    {
        "name": "Clean SQL without explanation",
        "raw": """SELECT * FROM passenger WHERE country = 'Germany' LIMIT 5;"""
    },
    {
        "name": "SQL with 'IN this example' explanation (tricky case)",
        "raw": """SELECT a.*
FROM airport_geo AS a
JOIN fliight AS f ON a.iata = f.iata
JOIN passenger AS p ON f.iata = p.iata
LEFT JOIN
  (SELECT a.*,
          b.name AS airline_name
   FROM airline_geo AS a
   LEFT JOIN airline AS b ON a.iata = b.iata) AS al ON a.iata = al.iata
WHERE p.iata = '115'
  AND f.flight_id = 1234;

IN this example, we ARE USING the `LEFT JOIN` clause TO JOIN the `airline_geo`, `passenger`, AND `airline` TABLES FOR a SPECIFIC flight number (`115`) WITH the `flight_info` table. The resulting SQL query will ONLY RETURN the DATA FROM the `passenger` TABLE, INCLUDING the `name` COLUMN OF the `airline_geo` table."""
    }
]

console.print("\n[bold cyan]Testing SQL Cleaning & Separation[/bold cyan]\n")
console.print("=" * 70 + "\n")

for i, test in enumerate(test_cases, 1):
    console.print(f"[bold]Test {i}: {test['name']}[/bold]\n")
    
    # Show raw input
    console.print("[dim]Raw LLM Output:[/dim]")
    console.print(f"[dim]{test['raw'][:200]}{'...' if len(test['raw']) > 200 else ''}[/dim]\n")
    
    # Clean and display
    cleaned = clean_sql(test['raw'])
    pretty_print_sql(cleaned, title=f"Cleaned SQL - Test {i}")
    
    console.print("\n" + "-" * 70 + "\n")
