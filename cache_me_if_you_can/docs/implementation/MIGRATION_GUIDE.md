# Migration Guide: Using Core Connection Modules

This guide helps developers migrate existing code or write new code using the centralized connection modules.

## Quick Start

### For New Code

```python
# Database connections
from core import get_db_engine
from sqlalchemy import text

engine = get_db_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM table"))

# Cache connections
from core import get_cache_client

cache = get_cache_client()
cache.set("key", "value", ttl=3600)
value = cache.get("key")
cache.close()
```

## Detailed Migration Examples

### Example 1: Migrating Database Connection Code

#### Before
```python
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

class MyClass:
    def __init__(self):
        # Duplicate connection logic
        db_type = os.getenv("DB_ENGINE", "mysql").lower()
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_user = os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "flughafendb_large")
        
        if db_type in ["mysql", "mariadb"]:
            connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        elif db_type == "postgresql":
            connection_string = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            raise ValueError(f"Unsupported DB_ENGINE: {db_type}")
        
        self.engine = create_engine(connection_string)
```

#### After
```python
from core import get_db_engine

class MyClass:
    def __init__(self):
        # Clean, simple connection
        self.engine = get_db_engine()
```

**Lines saved: ~20 lines per file**

---

### Example 2: Migrating Cache Connection Code

#### Before
```python
import os
try:
    import valkey
except ImportError:
    import redis as valkey

class MyCache:
    def __init__(self):
        cache_type = os.getenv("CACHE_ENGINE", "redis").lower()
        cache_host = os.getenv("CACHE_HOST", "localhost")
        cache_port = int(os.getenv("CACHE_PORT", "6379"))
        
        if cache_type in ["redis", "valkey"]:
            self.client = valkey.Redis(
                host=cache_host,
                port=cache_port,
                decode_responses=True
            )
        elif cache_type == "memcached":
            from pymemcache.client import base
            self.client = base.Client((cache_host, cache_port))
        else:
            raise ValueError(f"Unsupported CACHE_ENGINE: {cache_type}")
    
    def get(self, key):
        if cache_type in ["redis", "valkey"]:
            return self.client.get(key)
        elif cache_type == "memcached":
            value = self.client.get(key)
            return value.decode() if value else None
    
    def set(self, key, value, ttl):
        if cache_type in ["redis", "valkey"]:
            self.client.setex(key, ttl, value)
        elif cache_type == "memcached":
            self.client.set(key, value.encode(), expire=ttl)
```

#### After
```python
from core import get_cache_client

class MyCache:
    def __init__(self):
        # Unified cache interface
        self.cache = get_cache_client()
    
    def get(self, key):
        return self.cache.get(key)
    
    def set(self, key, value, ttl):
        self.cache.set(key, value, ttl)
```

**Lines saved: ~30 lines per file**

---

### Example 3: Using Context Managers

#### Database with Context Manager
```python
from core import get_db_connection
from sqlalchemy import text

# Automatic cleanup
with get_db_connection() as db:
    with db.connect() as conn:
        result = conn.execute(text("SELECT * FROM users"))
        for row in result:
            print(row)
# Connection automatically disposed
```

#### Cache with Context Manager
```python
from core import get_cache_client

# Automatic cleanup
with get_cache_client() as cache:
    cache.set("user:1", "John Doe", ttl=3600)
    user = cache.get("user:1")
    print(user)
# Connection automatically closed
```

---

### Example 4: Custom Configuration

#### Override Environment Variables
```python
from core import get_db_engine, get_cache_client

# Custom database connection
custom_db = get_db_engine(
    db_type="postgresql",
    host="custom-host.example.com",
    port="5432",
    user="custom_user",
    password="custom_pass",
    database="custom_db"
)

# Custom cache connection
custom_cache = get_cache_client(
    cache_type="memcached",
    host="cache.example.com",
    port=11211
)
```

---

### Example 5: Connection Pooling

```python
from core import get_db_engine

# With custom pool settings
engine = get_db_engine(
    pool_size=20,           # Number of connections to maintain
    max_overflow=10,        # Additional connections when pool is full
    pool_timeout=30,        # Seconds to wait for connection
    pool_recycle=3600       # Recycle connections after 1 hour
)
```

---

## Common Patterns

### Pattern 1: Cache-Aside (Lazy Loading)

```python
from core import get_db_engine, get_cache_client
from sqlalchemy import text
import json

class DataService:
    def __init__(self):
        self.db = get_db_engine()
        self.cache = get_cache_client()
    
    def get_user(self, user_id):
        cache_key = f"user:{user_id}"
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Cache miss - query database
        with self.db.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM users WHERE id = :id"),
                {"id": user_id}
            )
            user = dict(result.fetchone()._mapping)
        
        # Store in cache
        self.cache.set(cache_key, json.dumps(user), ttl=3600)
        return user
```

### Pattern 2: Write-Through Cache

```python
from core import get_db_engine, get_cache_client
from sqlalchemy import text
import json

class DataService:
    def __init__(self):
        self.db = get_db_engine()
        self.cache = get_cache_client()
    
    def update_user(self, user_id, data):
        # Update database first
        with self.db.begin() as conn:
            conn.execute(
                text("UPDATE users SET name = :name WHERE id = :id"),
                {"id": user_id, "name": data["name"]}
            )
        
        # Update cache immediately
        cache_key = f"user:{user_id}"
        self.cache.set(cache_key, json.dumps(data), ttl=3600)
```

### Pattern 3: Cache Invalidation

```python
from core import get_cache_client

class CacheManager:
    def __init__(self):
        self.cache = get_cache_client()
    
    def invalidate_user(self, user_id):
        """Invalidate user cache"""
        cache_key = f"user:{user_id}"
        self.cache.delete(cache_key)
    
    def invalidate_pattern(self, pattern):
        """Invalidate all keys matching pattern (Redis/Valkey only)"""
        # Note: This requires direct client access
        keys = self.cache.client.keys(pattern)
        for key in keys:
            self.cache.delete(key)
```

---

## Testing

### Mocking Database Connections

```python
from unittest.mock import Mock, patch
from core import get_db_engine

def test_my_function():
    # Mock the engine
    with patch('core.get_db_engine') as mock_get_engine:
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Your test code here
        result = my_function()
        
        # Verify engine was used
        mock_engine.connect.assert_called_once()
```

### Mocking Cache Connections

```python
from unittest.mock import Mock, patch
from core import get_cache_client

def test_cache_function():
    # Mock the cache
    with patch('core.get_cache_client') as mock_get_cache:
        mock_cache = Mock()
        mock_cache.get.return_value = "cached_value"
        mock_get_cache.return_value = mock_cache
        
        # Your test code here
        result = my_cache_function()
        
        # Verify cache was used
        mock_cache.get.assert_called_once_with("my_key")
```

---

## Troubleshooting

### Issue: Import Error

**Problem:**
```python
ImportError: cannot import name 'get_db_engine' from 'core'
```

**Solution:**
Make sure you're in the project root directory or add the parent directory to your Python path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_db_engine
```

### Issue: Connection Refused

**Problem:**
```
ConnectionError: Error connecting to database/cache
```

**Solution:**
1. Check your `.env` file has correct values
2. Verify the database/cache service is running
3. Test connection manually:
```bash
# Test database
mysql -h localhost -u root -p

# Test cache
redis-cli ping
# or
valkey-cli ping
```

### Issue: Environment Variables Not Loading

**Problem:**
Connection uses default values instead of `.env` values

**Solution:**
Make sure `load_dotenv()` is called before importing core modules:
```python
from dotenv import load_dotenv
load_dotenv()  # Must be before core imports

from core import get_db_engine, get_cache_client
```

---

## Best Practices

### 1. Always Use Context Managers When Possible
```python
# ✅ Good - automatic cleanup
with get_db_connection() as db:
    with db.connect() as conn:
        result = conn.execute(query)

# ❌ Avoid - manual cleanup required
db = get_db_connection()
conn = db.connect()
result = conn.execute(query)
db.dispose()  # Easy to forget!
```

### 2. Close Connections Explicitly in Long-Running Processes
```python
# ✅ Good - explicit cleanup
cache = get_cache_client()
try:
    cache.set("key", "value")
finally:
    cache.close()
```

### 3. Use Environment Variables for Configuration
```python
# ✅ Good - configurable via .env
engine = get_db_engine()

# ❌ Avoid - hardcoded values
engine = get_db_engine(
    host="hardcoded-host",
    password="hardcoded-password"
)
```

### 4. Handle Connection Errors Gracefully
```python
from core import get_db_engine

try:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(query)
except Exception as e:
    logger.error(f"Database error: {e}")
    # Fallback logic or error response
```

---

## Additional Resources

- **Core Module Documentation:** `core/README.md`
- **Refactoring Summary:** `docs/REFACTORING_SUMMARY.md`
- **Architecture Diagrams:** `docs/REFACTORING_DIAGRAM.md`
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **Redis/Valkey Docs:** https://redis.io/docs/
