# Core Connection Modules

This folder contains centralized connection management modules for the project, eliminating redundant connection code across the codebase.

## Modules

### `rdbms.py` - Relational Database Connection Manager

Provides centralized connection management for relational databases using SQLAlchemy.

**Supported Databases:**
- MySQL
- MariaDB  
- PostgreSQL

**Features:**
- Environment variable configuration
- Connection pooling support
- Context manager support
- Factory functions for easy instantiation

**Usage:**

```python
from core import get_db_engine, get_db_connection
from sqlalchemy import text

# Option 1: Get engine directly
engine = get_db_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM table"))

# Option 2: Use connection wrapper with context manager
with get_db_connection() as db:
    with db.connect() as conn:
        result = conn.execute(text("SELECT * FROM table"))
```

**Environment Variables:**
- `DB_ENGINE`: Database type (mysql, mariadb, postgresql) - default: mysql
- `DB_HOST`: Database host - default: localhost
- `DB_PORT`: Database port - default: 3306
- `DB_USER`: Database user - default: root
- `DB_PASSWORD`: Database password - default: empty
- `DB_NAME`: Database name - default: flughafendb_large

### `inmemory.py` - In-Memory Cache Connection Manager

Provides centralized connection management for in-memory cache systems.

**Supported Cache Engines:**
- Redis
- Valkey
- Memcached

**Features:**
- Environment variable configuration
- Unified API across different cache backends
- TTL support
- Distributed locking (Redis/Valkey)
- Context manager support

**Usage:**

```python
from core import get_cache_client

# Basic usage
cache = get_cache_client()

# Set value with TTL
cache.set("key", "value", ttl=3600)

# Get value
value = cache.get("key")

# Delete value
cache.delete("key")

# Cleanup
cache.close()

# Or use context manager
with get_cache_client() as cache:
    cache.set("key", "value", ttl=60)
    value = cache.get("key")
```

**Environment Variables:**
- `CACHE_ENGINE`: Cache engine type (redis, valkey, memcached) - default: redis
- `CACHE_HOST`: Cache host - default: localhost
- `CACHE_PORT`: Cache port - default: 6379

## Benefits of Refactoring

### Before Refactoring
Each file had its own connection logic:
- Duplicate code across multiple files
- Inconsistent error handling
- Hard to maintain and update
- Difficult to test

### After Refactoring
Centralized connection management:
- ✅ Single source of truth for connections
- ✅ Consistent error handling
- ✅ Easy to maintain and update
- ✅ Simplified testing
- ✅ Reduced code duplication
- ✅ Better separation of concerns

## Files Refactored

The following files were updated to use the core connection modules:

1. **`daos/cache_aside.py`** - Cache-aside pattern implementation
2. **`daos/nlp_to_sql.py`** - NLP to SQL converter (no changes needed)
3. **`airport_app.py`** - Streamlit airport application
4. **`samples/demo_cache_aside.py`** - Cache-aside demo (uses daos module)
5. **`samples/demo_weather_api_cache.py`** - Weather API cache demo
6. **`samples/demo_write_through_cache.py`** - Write-through cache demo
7. **`samples/demo_multi_threaded_performance.py`** - Multi-threaded performance test

## Migration Guide

### For Database Connections

**Before:**
```python
from sqlalchemy import create_engine

db_type = os.getenv("DB_ENGINE", "mysql")
db_host = os.getenv("DB_HOST", "localhost")
# ... more config
connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
engine = create_engine(connection_string)
```

**After:**
```python
from core import get_db_engine

engine = get_db_engine()
```

### For Cache Connections

**Before:**
```python
try:
    import valkey
except ImportError:
    import redis as valkey

cache_type = os.getenv("CACHE_ENGINE", "redis")
cache_host = os.getenv("CACHE_HOST", "localhost")
cache_port = int(os.getenv("CACHE_PORT", "6379"))

if cache_type in ["redis", "valkey"]:
    client = valkey.Redis(host=cache_host, port=cache_port, decode_responses=True)
# ... handle other cache types
```

**After:**
```python
from core import get_cache_client

cache = get_cache_client()
```

## Testing

To test the connection modules:

```bash
# Test RDBMS connection
python core/rdbms.py

# Test in-memory cache connection
python core/inmemory.py
```

## Future Enhancements

Potential improvements for the core modules:

1. **Connection Pooling Configuration** - More granular control over pool settings
2. **Retry Logic** - Automatic retry on connection failures
3. **Health Checks** - Built-in connection health monitoring
4. **Metrics Collection** - Connection usage statistics
5. **Multiple Database Support** - Connect to multiple databases simultaneously
6. **Async Support** - Async/await support for async frameworks
