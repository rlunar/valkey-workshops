# Hands-On Caching Workshop

Build cache-aside and write-through patterns from scratch.

## Setup

```bash
# Ensure database and cache are running
mysql -u root -p -e "SELECT 1"
valkey-cli ping

# Check environment
cat .env
```

## Exercise 1: Cache-Aside Pattern

Create `cache_aside.py`:

```python
import json
import time
import logging
from sqlalchemy import text
from core import get_db_engine, get_cache_client

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def query_with_cache(query, params=None):
    cache, engine = get_cache_client(), get_db_engine()
    key = f"q:{hash(query + str(params))}"
    
    start = time.time()
    cached = cache.get(key)
    if cached:
        logger.info(f"CACHE: {(time.time()-start)*1000:.1f}ms")
        return json.loads(cached)
    
    start = time.time()
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(query), params or {})]
    cache.set(key, json.dumps(rows, default=str), 300)
    logger.info(f"DB: {(time.time()-start)*1000:.1f}ms")
    return rows

if __name__ == "__main__":
    # Simple query
    query_with_cache("SELECT name FROM airport WHERE airport_id = :id", {"id": 3797})
    query_with_cache("SELECT name FROM airport WHERE airport_id = :id", {"id": 3797})
```

Run:
```bash
uv run python hands_on/cache_aside.py
```

## Exercise 2: Write-Through Pattern

Create `write_through.py`:

```python
import json
import time
import logging
from sqlalchemy import text
from core import get_db_engine, get_cache_client

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def write_through(table, data, id_field):
    cache, engine = get_cache_client(), get_db_engine()
    
    # Write to database first
    start = time.time()
    columns = ', '.join(data.keys())
    placeholders = ', '.join([f":{k}" for k in data.keys()])
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    
    with engine.connect() as conn:
        result = conn.execute(text(query), data)
        conn.commit()
        record_id = result.lastrowid or data.get(id_field)
    db_time = (time.time() - start) * 1000
    
    # Write to cache
    start = time.time()
    cache_key = f"{table}:{record_id}"
    cache.set(cache_key, json.dumps(data, default=str), 300)
    cache_time = (time.time() - start) * 1000
    
    logger.info(f"DB: {db_time:.1f}ms, CACHE: {cache_time:.1f}ms")
    return record_id

if __name__ == "__main__":
    passenger_data = {"firstname": "John", "lastname": "Doe", "passportno": "P999999"}
    write_through("passenger", passenger_data, "passenger_id")
```

Run:
```bash
uv run python hands_on/write_through.py
```

## Key Concepts

**Cache-Aside**: Check cache first, query DB on miss, store result
**Write-Through**: Write to DB first, then update cache

## Expected Output

Cache-aside shows latency difference:
```
DB: 15.2ms
CACHE: 0.3ms
```

Write-through shows both operations:
```
DB: 8.1ms, CACHE: 0.2ms
```