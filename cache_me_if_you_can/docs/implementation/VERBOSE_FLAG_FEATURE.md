# Verbose Flag Feature

## Overview

Added a `--verbose` (or `-v`) flag to `daos/nlp_to_sql.py` that displays the full prompt sent to the LLM for the first query. This is useful for debugging and understanding what context is being provided to the model.

## Usage

```bash
# Demo mode with verbose
python daos/nlp_to_sql.py --verbose
python daos/nlp_to_sql.py -v  # Short form

# Interactive mode with verbose
python daos/nlp_to_sql.py --verbose interactive
python daos/nlp_to_sql.py -v interactive

# With specific model
python daos/nlp_to_sql.py tinyllama --verbose
python daos/nlp_to_sql.py codellama -v interactive
```

## What It Shows

When `--verbose` is enabled, the tool displays:

1. **Full Prompt**: The complete prompt sent to the LLM, including:
   - Database schema overview
   - All 14 table schemas with columns and foreign keys
   - Query patterns and examples
   - Conversion rules
   - The user's natural language query

2. **Display Format**: The prompt is shown in a yellow-bordered panel before the first query is executed

3. **Frequency**: Only shown for the **first query** to avoid cluttering the output

## Example Output

```
📝 Full Prompt (first query only):
╭─────────────────── Prompt sent to LLM ───────────────────╮
│ You are a SQL query generator for the Flughafen         │
│ airport database.                                        │
│                                                          │
│ === DATABASE OVERVIEW ===                               │
│ Database: flughafendb_large                             │
│ Description: Airport management database...             │
│                                                          │
│ TABLES:                                                 │
│ - airport: Master table of airports...                  │
│ - flight: Individual flight instances...                │
│ ...                                                     │
│                                                          │
│ === TABLE SCHEMAS ===                                   │
│ AIRPORT:                                                │
│ Columns: airport_id (INT), name (VARCHAR)...           │
│ ...                                                     │
│                                                          │
│ Natural Language Query: Get airport by IATA code JFK    │
│                                                          │
│ SQL Query:                                              │
╰──────────────────────────────────────────────────────────╯
```

## Benefits

1. **Debugging**: See exactly what context the LLM receives
2. **Optimization**: Identify if too much or too little context is provided
3. **Understanding**: Learn how the knowledge base is structured in the prompt
4. **Token Analysis**: Verify the estimated token count matches the actual prompt size

## Implementation Details

### Argument Parsing

The tool now supports flexible argument ordering:

```python
# Parse arguments
model = None
mode = "demo"
verbose = False

args = sys.argv[1:]
for arg in args:
    if arg == "--verbose" or arg == "-v":
        verbose = True
    elif arg == "interactive":
        mode = "interactive"
    elif not arg.startswith("-"):
        model = arg
```

### Function Signatures

Both mode functions now accept a `verbose` parameter:

```python
def demo_mode(converter: NLPToSQL, verbose: bool = False):
    # Shows prompt for first query if verbose=True
    
def interactive_mode(converter: NLPToSQL, verbose: bool = False):
    # Shows prompt for first query if verbose=True
```

### Prompt Display

Uses Rich's `Panel` component for clean formatting:

```python
if verbose and first_query:
    prompt = converter._build_prompt(query)
    console.print("\n[bold yellow]📝 Full Prompt (first query only):[/bold yellow]")
    console.print(Panel(
        prompt,
        title="Prompt sent to LLM",
        border_style="yellow",
        expand=False
    ))
    first_query = False
```

## Use Cases

1. **Development**: Verify knowledge base is loaded correctly
2. **Debugging**: Troubleshoot why certain queries produce unexpected results
3. **Optimization**: Identify redundant or missing context
4. **Documentation**: Generate examples of prompts for documentation
5. **Learning**: Understand prompt engineering for SQL generation

## Related Files

- `daos/nlp_to_sql.py` - Main implementation
- `ENHANCEMENTS_SUMMARY.md` - Updated usage documentation
- `test_verbose_flag.sh` - Test script with examples
