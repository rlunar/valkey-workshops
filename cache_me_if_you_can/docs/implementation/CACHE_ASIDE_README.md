# Cache-Aside Pattern Implementation

A flexible Python implementation of the cache-aside (lazy loading) pattern supporting multiple database and cache engines.

## Features

- **Multiple Database Engines**: MySQL, MariaDB, PostgreSQL
- **Multiple Cache Engines**: Redis, Valkey, Memcached
- **Automatic Cache Key Generation**: Uses SHA256 hash of SQL query
- **Configurable TTL**: Set cache expiration per query or use default
- **Cache Invalidation**: Manually invalidate specific queries
- **Force Refresh**: Bypass cache and refresh from database
- **Performance Metrics**: Returns latency and cache hit/miss status

## Installation

Install required dependencies:

```bash
# For MySQL/MariaDB
uv add sqlalchemy pymysql python-dotenv redis pymemcache

# For PostgreSQL
uv add sqlalchemy psycopg2-binary python-dotenv redis pymemcache
```

## Configuration

Create a `.env` file in the samples directory (copy from `.env.example`):

```bash
# Database Configuration
DB_ENGINE=mysql          # mysql, mariadb, or postgresql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=airportdb

# Cache Configuration
CACHE_ENGINE=redis       # redis, valkey, or memcached
CACHE_HOST=localhost
CACHE_PORT=6379

# Cache TTL (seconds)
CACHE_TTL=3600          # 1 hour default
```

## Usage

### Basic Example

```python
from cache_aside import CacheAside

# Initialize
cache = CacheAside()

# Execute query with caching
query = "SELECT * FROM airline WHERE airline_id = 1"
results, source, latency = cache.execute_query(query)

print(f"Source: {source}")        # "CACHE_HIT" or "CACHE_MISS"
print(f"Latency: {latency:.2f} ms")
print(f"Results: {results}")

# Cleanup
cache.close()
```

### Advanced Usage

```python
from cache_aside import CacheAside

cache = CacheAside()

# Custom TTL (5 minutes)
results, source, latency = cache.execute_query(
    query="SELECT * FROM passenger WHERE passenger_id = 1000",
    ttl=300
)

# Force refresh (bypass cache)
results, source, latency = cache.execute_query(
    query="SELECT * FROM flight WHERE flight_id = 115",
    force_refresh=True
)

# Invalidate specific query
query = "SELECT * FROM airline WHERE airline_id = 1"
cache.invalidate_query(query)

cache.close()
```

## How It Works

### Cache Key Generation

Cache keys are generated using SHA256 hash of the SQL query:

```
query:<sha256_hash>
```

Example:
```
query:a3f5b8c9d2e1f4a7b6c5d8e9f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0
```

### Cache-Aside Flow

1. **Check Cache**: Look for cached result using query hash
2. **Cache Hit**: Return cached data (fast)
3. **Cache Miss**: Query database, cache result, return data
4. **TTL Expiration**: Cached data expires after TTL seconds

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     Hit      ┌─────────────┐
│    Cache    │─────────────▶│   Return    │
└──────┬──────┘              └─────────────┘
       │ Miss
       ▼
┌─────────────┐
│  Database   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Update Cache│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Return    │
└─────────────┘
```

## Performance Comparison

Typical latency improvements:

| Query Type | Database | Cache | Improvement |
|------------|----------|-------|-------------|
| Simple (1 table) | 5-20 ms | 0.5-2 ms | 5-10x faster |
| Medium (2-3 tables) | 20-100 ms | 0.5-2 ms | 10-50x faster |
| Advanced (4+ tables) | 100-500 ms | 0.5-2 ms | 50-250x faster |

## Supported Configurations

### Database Engines

| Engine | Connection String | Driver |
|--------|------------------|--------|
| MySQL | `mysql+pymysql://...` | pymysql |
| MariaDB | `mysql+pymysql://...` | pymysql |
| PostgreSQL | `postgresql+psycopg2://...` | psycopg2 |

### Cache Engines

| Engine | Port | Client Library |
|--------|------|----------------|
| Redis | 6379 | redis-py |
| Valkey | 6379 | redis-py |
| Memcached | 11211 | pymemcache |

## Best Practices

### TTL Selection

- **Static data** (airlines, airports): 1-24 hours
- **Semi-static** (flight schedules): 15-60 minutes
- **Dynamic** (bookings, availability): 1-5 minutes
- **Real-time** (flight status): Don't cache or use 10-30 seconds

### Cache Invalidation

Invalidate cache when data changes:

```python
# After updating a booking
cache.invalidate_query("SELECT * FROM booking WHERE booking_id = 123")

# After flight schedule change
cache.invalidate_query("SELECT * FROM flight WHERE flight_id = 456")
```

### Error Handling

The implementation gracefully handles cache failures:
- Cache GET errors return `None` (triggers database query)
- Cache SET errors are logged but don't block the response
- Database errors propagate to caller

## Running the Demo

```bash
cd samples
python cache_aside.py
```

Expected output:
```
============================================================
Cache-Aside Pattern Demo
============================================================

1. First execution (should be CACHE_MISS):
   Source: CACHE_MISS
   Latency: 15.23 ms
   Results: [{'airline_id': 1, 'iata': 'LH', ...}]

2. Second execution (should be CACHE_HIT):
   Source: CACHE_HIT
   Latency: 1.45 ms
   Results: [{'airline_id': 1, 'iata': 'LH', ...}]

3. Force refresh (bypasses cache):
   Source: CACHE_MISS
   Latency: 14.87 ms

4. Invalidating cache...
   Cache invalidated: True

5. Query after invalidation (should be CACHE_MISS):
   Source: CACHE_MISS
   Latency: 15.01 ms

============================================================
```

## Integration with Sample Queries

Use with the SQL samples in this directory:

```python
from cache_aside import CacheAside

cache = CacheAside()

# Load query from file
with open('01_simple_queries.sql') as f:
    queries = f.read().split(';')
    
# Execute first query with caching
results, source, latency = cache.execute_query(queries[0])
print(f"Query executed in {latency:.2f} ms from {source}")

cache.close()
```

## Troubleshooting

### Connection Errors

- Verify database is running and accessible
- Check credentials in `.env` file
- Ensure correct port numbers

### Cache Errors

- Verify Redis/Valkey/Memcached is running
- Check `CACHE_HOST` and `CACHE_PORT` settings
- Test connection: `redis-cli ping` or `telnet localhost 11211`

### Import Errors

Install missing dependencies:
```bash
pip install sqlalchemy pymysql python-dotenv redis pymemcache
```
