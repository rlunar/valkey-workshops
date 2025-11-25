# Cache-Aside (Lazy Loading)

## Overview

Cache-Aside, also known as Lazy Loading, is a caching strategy where the application is responsible for managing the cache. Data is loaded into the cache only when it's requested, not proactively. This pattern is called "lazy" because the cache is populated on-demand rather than ahead of time.

## How It Works

The Cache-Aside pattern follows a simple three-step process:

1. **Check the Cache First**: When the application needs data, it first checks if the data exists in the cache
2. **Cache Miss - Query the Database**: If the data isn't in the cache (a "miss"), the application queries the database directly
3. **Update the Cache**: After retrieving data from the database, the application stores it in the cache for future requests

This approach ensures that only frequently accessed data occupies cache space, making efficient use of memory resources.

## Benefits

- **Memory Efficiency**: Only stores data that's actually being used
- **Simple to Implement**: The application has full control over what gets cached and when
- **Resilient**: If the cache fails, the application can still function by querying the database
- **Flexible TTL**: Each cache entry can have its own expiration time

## Trade-offs

- **Initial Latency**: The first request for any data will always be slow (cache miss)
- **Cache Stampede Risk**: Multiple requests for the same uncached data can hit the database simultaneously
- **Stale Data Possible**: Cached data may become outdated if the database is updated directly

## Flow Diagram

```mermaid
graph LR
    A[Application]:::app --> B{Data in<br/>Cache?}:::decision
    B -->|Cache Miss| C[Database]:::db
    C --> D[Store in Cache]:::cache
    D --> A
    B -->|Cache Hit| A
    
    classDef app fill:#6983FF,stroke:#30176E,stroke-width:2px,color:#FFFDFA
    classDef decision fill:#BCB5E7,stroke:#30176E,stroke-width:2px,color:#1A2026
    classDef db fill:#E0A2AF,stroke:#642637,stroke-width:2px,color:#1A2026
    classDef cache fill:#D3DDE7,stroke:#30176E,stroke-width:2px,color:#1A2026
```

## Detailed Sequence

```mermaid
sequenceDiagram
    participant App as Application
    participant Cache as Valkey Cache
    participant RDBMS as Database
    
    rect rgb(188, 181, 231)
    Note over App,RDBMS: First Request (Cache Miss)
    App->>Cache: 1. GET query:<sql_hash>
    Cache-->>App: (nil) - Cache Miss
    App->>RDBMS: 2. SELECT * FROM airports WHERE code = 'JFK'
    RDBMS-->>App: Airport data (500ms)
    App->>Cache: 3. SETEX query:<sql_hash> 300 [data]
    Cache-->>App: OK
    App-->>App: Return data to user
    end
    
    rect rgb(211, 221, 231)
    Note over App,RDBMS: Subsequent Request (Cache Hit)
    App->>Cache: 4. GET query:<sql_hash>
    Cache-->>App: [cached data] (1ms) - Cache Hit! ⚡
    App-->>App: Return cached data
    end
    
    Note over Cache: TTL: 300 seconds (5 minutes)
```

## Implementation Pseudocode

```python
def get_data(query):
    """
    Cache-Aside pattern in simple pseudocode
    """
    # Generate a unique key for this query
    cache_key = hash(query)
    
    # Step 1: Check the cache first
    data = cache.get(cache_key)
    
    if data exists:
        # Cache Hit! Return immediately
        return data
    
    # Step 2: Cache Miss - Query the database
    data = database.execute(query)
    
    # Step 3: Store result in cache for next time
    cache.set(cache_key, data, ttl=300)  # Cache for 5 minutes
    
    return data
```

### Real-World Example

```python
# Example: Getting airport information
query = "SELECT * FROM airports WHERE code = 'JFK'"

# First call - Cache Miss (slow: ~500ms)
result = get_data(query)  # Queries database, stores in cache

# Second call - Cache Hit (fast: ~1ms)
result = get_data(query)  # Returns from cache instantly

# After 5 minutes, cache expires
# Next call - Cache Miss again (slow: ~500ms)
result = get_data(query)  # Queries database, refreshes cache
```

## When to Use Cache-Aside

✅ **Good For:**
- Read-heavy workloads where the same data is requested frequently
- Data that doesn't change often
- Applications where you want fine-grained control over caching logic
- Scenarios where cache failures shouldn't break the application

❌ **Not Ideal For:**
- Write-heavy workloads (consider Write-Through or Write-Behind)
- Data that must always be fresh and up-to-date
- Scenarios requiring cache warming at startup
