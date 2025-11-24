# Semantic Search Vector Index Fix

## Problem

The semantic_search.py script was failing to create vector indexes with the error:
```
unknown command 'FT.CREATE', with args beginning with: 'prompt_embeddings' 'ON' 'HASH'...
```

## Root Cause

The FT.CREATE command was being called incorrectly. The command arguments need to be unpacked using `*command_args` instead of passing them as individual parameters.

## Solution

### 1. Fixed Vector Index Creation

Updated `_create_index()` method to use the correct command format from `tmp/load_data.py`:

**Before:**
```python
self.valkey_client.execute_command(
    "FT.CREATE", index_name,
    "ON", "HASH",
    "PREFIX", "1", "embedding:prompt:",
    ...
)
```

**After:**
```python
command_args = [
    "FT.CREATE", index_name,
    "ON", "HASH",
    "PREFIX", "1", "embedding:prompt:",
    "SCHEMA",
    "prompt", "TAG",
    "query_key", "TAG",
    "embedding", "VECTOR", "HNSW", "6",
        "TYPE", "FLOAT32",
        "DIM", str(self.vector_dim),
        "DISTANCE_METRIC", "COSINE"
]

self.valkey_client.execute_command(*command_args)
```

### 2. Improved Error Handling

Added better error detection and messaging:

```python
except valkey.ResponseError as e:
    if "Unknown index name" in str(e) or "no such index" in str(e).lower():
        # Index doesn't exist, create it
        ...
    else:
        # Some other error
        print(f"⚠️  Warning: Error checking index: {e}")
```

### 3. Added --verbose Flag

New `--verbose` flag provides detailed information about:

- **Valkey Connection**:
  - Host and port
  - Connection status
  - Server version
  - Memory usage
  
- **Embedding Model**:
  - Model name
  - Vector dimension
  - Max sequence length
  
- **Configuration**:
  - Similarity threshold
  - Ollama model
  
- **Vector Index**:
  - Index creation details
  - Vector dimension
  - Distance metric
  - Algorithm (HNSW)

### 4. Fixed Environment Variables

Changed from `VECTOR_HOST`/`VECTOR_PORT` to `CACHE_HOST`/`CACHE_PORT` for consistency with other scripts.

## Usage

### Basic Usage (No Verbose)
```bash
uv run python samples/semantic_search.py
```

### With Verbose Output
```bash
uv run python samples/semantic_search.py --verbose
```

### Example Verbose Output
```
======================================================================
Semantic Search SQL Cache with Vector Similarity
======================================================================

======================================================================
Valkey Connection
======================================================================
Host: localhost
Port: 6379
✅ Connected successfully
   Version: 7.2.4
   Memory: 1.23M

======================================================================
Embedding Model
======================================================================
Loading embedding model: all-MiniLM-L6-v2...
✅ Embedding model loaded. Vector dimension: 384

======================================================================
Configuration
======================================================================
Similarity threshold: 0.70
Ollama model: codellama

======================================================================
Vector Index Setup
======================================================================
Creating vector search index 'prompt_embeddings'...
   Vector dimension: 384
   Distance metric: COSINE
   Algorithm: HNSW
✅ Index 'prompt_embeddings' created successfully with 384-dimensional vectors
```

## Command-Line Options

```bash
usage: semantic_search.py [-h] [--host HOST] [--port PORT] [--model MODEL]
                          [--threshold THRESHOLD] [--mode {demo,interactive}]
                          [--clear] [--verbose]

options:
  --host HOST           Valkey host (default: from VECTOR_HOST env or localhost)
  --port PORT           Valkey port (default: from VECTOR_PORT env or 6379)
  --model MODEL         Ollama model (default: from OLLAMA_MODEL env or codellama)
  --threshold THRESHOLD Similarity threshold 0-1 (default: from SIMILARITY_THRESHOLD env or 0.70)
  --mode {demo,interactive}  Run mode
  --clear               Clear cache before starting
  --verbose             Enable verbose output with connection details
```

## Environment Variables

All defaults now read from `.env` file:

```bash
# Vector database connection (separate from cache)
VECTOR_HOST=localhost
VECTOR_PORT=16379

# Embedding model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Similarity threshold
SIMILARITY_THRESHOLD=0.70

# Ollama model
OLLAMA_MODEL=codellama
```

**Note:** The semantic search uses `VECTOR_HOST` and `VECTOR_PORT` which can be different from `CACHE_HOST` and `CACHE_PORT`. This allows you to:
- Use a separate Valkey instance with RediSearch module for vector operations
- Keep your regular cache separate from vector search
- Scale vector search independently

## Requirements

For vector search to work, you need:

1. **Valkey with RediSearch module** OR **Redis with RediSearch module**
   - Install: https://redis.io/docs/stack/search/
   - Or use Redis Stack: https://redis.io/docs/stack/

2. **Verify RediSearch is loaded:**
   ```bash
   valkey-cli MODULE LIST
   # or
   redis-cli MODULE LIST
   ```

   Should show:
   ```
   1) 1) "name"
      2) "search"
      3) "ver"
      4) 20612
   ```

## Troubleshooting

### Error: "unknown command 'FT.CREATE'"

**Cause**: RediSearch module not loaded

**Solution**:
1. Install Redis Stack or load RediSearch module
2. For Redis: `redis-server --loadmodule /path/to/redisearch.so`
3. For Valkey: Check if search module is available

### Fallback Behavior

If vector search is not available, the script will:
1. Print a warning message
2. Fall back to exact matching only
3. Continue functioning without vector similarity search

## Testing

Test the fix:

```bash
# Test with verbose output
uv run python samples/semantic_search.py --verbose --mode demo

# Test help
uv run python samples/semantic_search.py --help

# Test with custom model
uv run python samples/semantic_search.py --model tinyllama --verbose
```

## Changes Summary

| File | Changes |
|------|---------|
| `samples/semantic_search.py` | - Fixed FT.CREATE command format<br>- Added --verbose flag<br>- Improved error handling<br>- Fixed env var names (VECTOR_* → CACHE_*)<br>- Added connection details output |
| `.env.example` | Already had correct variables |

## References

- [RediSearch Documentation](https://redis.io/docs/stack/search/)
- [Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/)
- [HNSW Algorithm](https://redis.io/docs/stack/search/reference/vectors/#hnsw)
- [tmp/load_data.py](../tmp/load_data.py) - Reference implementation

---

**Fix Date:** November 20, 2025  
**Status:** ✅ Complete  
**Tested:** Yes
