# Vector Database vs Cache Separation

## Overview

The workshop uses **separate configuration** for vector database and cache operations:

- **Cache** (`CACHE_HOST:CACHE_PORT`) - Used for general caching (cache-aside, write-through patterns)
- **Vector Database** (`VECTOR_HOST:VECTOR_PORT`) - Used for semantic search with vector embeddings

## Configuration

### In .env File

```bash
# Regular Cache (for cache-aside, write-through patterns)
CACHE_ENGINE=valkey
CACHE_HOST=localhost
CACHE_PORT=6379

# Vector Database (for semantic search)
VECTOR_ENGINE=valkey
VECTOR_HOST=localhost
VECTOR_PORT=16379
```

## Why Separate?

### 1. **Different Requirements**

| Feature | Cache | Vector Database |
|---------|-------|-----------------|
| Module Required | None (core Valkey) | RediSearch/Valkey Search |
| Data Type | Simple key-value, hashes | Vector embeddings (HNSW) |
| Operations | GET, SET, DELETE | FT.CREATE, FT.SEARCH |
| Use Case | Fast data retrieval | Similarity search |

### 2. **Independent Scaling**

- **Cache**: High read/write throughput, simple operations
- **Vector DB**: Complex vector operations, memory-intensive

### 3. **Module Isolation**

- Not all Valkey instances have RediSearch module
- Cache doesn't need vector search capabilities
- Vector search doesn't need cache patterns

### 4. **Resource Management**

- Vector operations are memory-intensive (embeddings)
- Cache operations are typically smaller
- Separate instances allow better resource allocation

## Deployment Scenarios

### Scenario 1: Development (Same Instance)

Use the same Valkey instance for both:

```bash
CACHE_HOST=localhost
CACHE_PORT=6379

VECTOR_HOST=localhost
VECTOR_PORT=6379  # Same as cache
```

**Pros:**
- Simple setup
- One instance to manage
- Lower resource usage

**Cons:**
- Cache and vector operations share resources
- Need RediSearch module even if only using cache

### Scenario 2: Production (Separate Instances)

Use different Valkey instances:

```bash
# Cache instance (no modules needed)
CACHE_HOST=cache.example.com
CACHE_PORT=6379

# Vector instance (with RediSearch module)
VECTOR_HOST=vector.example.com
VECTOR_PORT=16379
```

**Pros:**
- Independent scaling
- Isolated workloads
- Cache doesn't need RediSearch module
- Better performance isolation

**Cons:**
- More instances to manage
- Higher resource usage

### Scenario 3: Hybrid (Local Dev + Remote Vector)

Cache locally, vector search remotely:

```bash
# Local cache for development
CACHE_HOST=localhost
CACHE_PORT=6379

# Remote vector database with RediSearch
VECTOR_HOST=vector-dev.example.com
VECTOR_PORT=16379
```

**Pros:**
- Fast local cache
- Shared vector database across team
- No need to install RediSearch locally

## Scripts Using Each Configuration

### Using CACHE_HOST/CACHE_PORT

- `daos/cache_aside.py` - Cache-aside pattern
- `samples/cache_aside_demo.py` - Cache-aside demo
- `samples/write_through_cache_demo.py` - Write-through cache
- `samples/weather_api_cache.py` - Weather API caching
- `airport_app.py` - Streamlit application

### Using VECTOR_HOST/VECTOR_PORT

- `samples/semantic_search.py` - Semantic search with vector embeddings

## Setup Instructions

### Option 1: Single Instance (Development)

1. **Start Valkey with RediSearch:**
   ```bash
   # Using Docker
   docker run -d -p 6379:6379 redis/redis-stack-server:latest
   
   # Or using Valkey with search module
   valkey-server --loadmodule /path/to/search.so
   ```

2. **Configure .env:**
   ```bash
   CACHE_HOST=localhost
   CACHE_PORT=6379
   VECTOR_HOST=localhost
   VECTOR_PORT=6379  # Same instance
   ```

### Option 2: Separate Instances (Production)

1. **Start Cache Instance:**
   ```bash
   # Standard Valkey (no modules)
   docker run -d -p 6379:6379 valkey/valkey:latest
   ```

2. **Start Vector Instance:**
   ```bash
   # Valkey with RediSearch
   docker run -d -p 16379:6379 redis/redis-stack-server:latest
   ```

3. **Configure .env:**
   ```bash
   CACHE_HOST=localhost
   CACHE_PORT=6379
   VECTOR_HOST=localhost
   VECTOR_PORT=16379  # Different instance
   ```

## Verification

### Check Cache Connection

```bash
# Test cache
valkey-cli -p 6379 PING
# Should return: PONG

# Test basic operations
valkey-cli -p 6379 SET test "hello"
valkey-cli -p 6379 GET test
```

### Check Vector Database Connection

```bash
# Test vector database
valkey-cli -p 16379 PING
# Should return: PONG

# Check if RediSearch module is loaded
valkey-cli -p 16379 MODULE LIST
# Should show: search module

# Test vector index creation
valkey-cli -p 16379 FT.CREATE test_idx ON HASH PREFIX 1 test: SCHEMA name TEXT
```

## Troubleshooting

### Issue: semantic_search.py can't connect

**Check:**
```bash
# Is vector database running?
valkey-cli -p 16379 PING

# Is VECTOR_PORT correct in .env?
grep VECTOR_PORT .env
```

### Issue: "unknown command 'FT.CREATE'"

**Cause:** RediSearch module not loaded on vector database

**Solution:**
```bash
# Check modules
valkey-cli -p 16379 MODULE LIST

# If empty, restart with module:
valkey-server --port 16379 --loadmodule /path/to/redisearch.so

# Or use Redis Stack:
docker run -d -p 16379:6379 redis/redis-stack-server:latest
```

### Issue: Cache demos work but semantic search doesn't

**Cause:** Different ports, vector database not running

**Solution:**
```bash
# Check both instances
valkey-cli -p 6379 PING   # Cache
valkey-cli -p 16379 PING  # Vector

# Start vector database if needed
docker run -d -p 16379:6379 redis/redis-stack-server:latest
```

## Performance Considerations

### Cache Instance (Port 6379)

- **Workload**: High-frequency reads/writes
- **Data Size**: Small to medium (KB range)
- **Operations**: Simple GET/SET/DELETE
- **Memory**: Moderate (depends on cache size)

### Vector Instance (Port 16379)

- **Workload**: Complex similarity searches
- **Data Size**: Large (embeddings are 384-1024 dimensions)
- **Operations**: Vector search (FT.SEARCH with KNN)
- **Memory**: High (vector indexes are memory-intensive)

## Migration Path

### From Single to Separate Instances

1. **Export vector data:**
   ```bash
   valkey-cli -p 6379 --scan --pattern "embedding:*" | \
     xargs valkey-cli -p 6379 DUMP > vector_data.txt
   ```

2. **Start new vector instance:**
   ```bash
   docker run -d -p 16379:6379 redis/redis-stack-server:latest
   ```

3. **Update .env:**
   ```bash
   VECTOR_PORT=16379
   ```

4. **Recreate indexes:**
   ```bash
   uv run python samples/semantic_search.py --clear
   ```

## Best Practices

1. **Development**: Use same instance (simpler)
2. **Staging**: Use separate instances (test production setup)
3. **Production**: Always use separate instances (better isolation)
4. **Monitoring**: Monitor both instances separately
5. **Backups**: Backup vector database separately (large data)

## References

- [RediSearch Module](https://redis.io/docs/stack/search/)
- [Vector Similarity Search](https://redis.io/docs/stack/search/reference/vectors/)
- [Valkey Documentation](https://valkey.io/docs/)

---

**Document Date:** November 20, 2025  
**Status:** ✅ Complete
