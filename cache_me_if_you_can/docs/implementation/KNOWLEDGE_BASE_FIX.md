# Knowledge Base Path Fix

## Problem

The knowledge base was not loading properly when running the script from different directories. The prompt showed mostly empty sections:

```
=== TABLE SCHEMAS ===

=== EXAMPLE QUERIES ===
```

This resulted in only ~47 characters of context instead of the expected ~9,644 characters.

## Root Cause

The `.env` file had a relative path `../knowledge_base` which was interpreted relative to the current working directory, not the script's location. This caused the path resolution to fail when running from different directories.

## Solution

### 1. Updated Path Resolution Logic

Modified `daos/nlp_to_sql.py` to resolve relative paths relative to the script's location:

```python
if knowledge_base_path is None:
    kb_path_env = os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base")
    # If path is relative, make it relative to the script's directory
    if not os.path.isabs(kb_path_env):
        # Get the directory where this script is located
        script_dir = Path(__file__).parent.parent
        knowledge_base_path = str(script_dir / kb_path_env)
    else:
        knowledge_base_path = kb_path_env
```

### 2. Updated .env Configuration

Changed the path to be simpler and more portable:

```bash
# Before
KNOWLEDGE_BASE_PATH=../knowledge_base

# After
KNOWLEDGE_BASE_PATH=knowledge_base
```

## Results

### Before Fix
- Context: 4 lines, 47 chars
- Estimated tokens: ~11
- Empty table schemas and examples

### After Fix
- Context: 150 lines, 9,644 chars
- Estimated tokens: ~2,411
- Full database overview with 14 tables
- Complete table schemas with columns, types, foreign keys, indexes
- Query patterns and examples

## Verbose Output Example

With `--verbose` flag, the prompt now shows:

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
│ - airport_geo: Geographic coordinates...                │
│ - flight: Individual flight instances...                │
│ ... (14 tables total)                                   │
│                                                          │
│ === TABLE SCHEMAS ===                                   │
│                                                          │
│ AIRPORT:                                                │
│ Description: Master table of airports...                │
│ Columns: airport_id (smallint), iata (char(3))...      │
│ Foreign Keys: ...                                       │
│ Indexes: icao_unq, name_idx, iata_idx                  │
│                                                          │
│ ... (detailed schemas for all 14 tables)                │
│                                                          │
│ === QUERY PATTERNS ===                                  │
│ ... (patterns and examples)                             │
│                                                          │
│ Natural Language Query: Get airport by IATA code JFK    │
│                                                          │
│ SQL Query:                                              │
╰──────────────────────────────────────────────────────────╯
```

## Benefits

1. **Consistent Behavior**: Works regardless of where the script is run from
2. **Better Context**: LLM receives full database schema and examples
3. **Improved Quality**: More context leads to better SQL generation
4. **Easier Debugging**: Verbose flag shows exactly what the LLM receives

## Testing

To verify the fix works:

```bash
# From project root
python daos/nlp_to_sql.py --verbose

# From daos directory
cd daos && python nlp_to_sql.py --verbose

# From any directory
python /path/to/daos/nlp_to_sql.py --verbose
```

All should show the same rich context with ~2,411 tokens.
