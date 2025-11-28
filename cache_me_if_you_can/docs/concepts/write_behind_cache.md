# Write-Behind (Write-Back)

## Overview

Write-Behind, also known as Write-Back, is a high-performance caching strategy that prioritizes write speed over immediate consistency. When data is written or updated, the application writes to the cache immediately and returns success, while the database update happens asynchronously in the background. This provides the fastest possible write performance at the cost of eventual consistency.

## How It Works

The Write-Behind pattern follows an asynchronous write process:

1. **Application Initiates Write**: When data needs to be created or updated, the application starts the write operation
2. **Write to Cache Immediately**: The data is written to the cache and the operation returns success instantly
3. **Queue Database Update**: The database update is queued for background processing
4. **Async Worker Processes Queue**: A separate background worker periodically processes the queue and updates the database

This approach maximizes write throughput by decoupling the fast cache write from the slower database write.

## Benefits

- **Maximum Write Performance**: Writes complete in milliseconds (cache speed)
- **High Throughput**: Can handle massive write volumes without database bottlenecks
- **Batch Processing**: Database updates can be batched for efficiency
- **Reduced Database Load**: Database writes are smoothed out over time
- **Resilience**: Application continues working even if database is temporarily slow

## Trade-offs

- **Eventual Consistency**: Cache and database are temporarily out of sync
- **Data Loss Risk**: If cache fails before queue is processed, updates may be lost
- **Complexity**: Requires background workers and queue management
- **Stale Reads from Database**: Direct database queries may return outdated data
- **Ordering Challenges**: Must ensure updates are applied in correct order

## Flow Diagram

```mermaid
graph LR
    A[Application<br/>Write]:::app --> B[Cache<br/>Update]:::cache
    B --> C[Queue<br/>Task]:::queue
    C --> D[Return<br/>Success ⚡]:::success
    E[Background<br/>Worker]:::worker --> F[Process<br/>Queue]:::queue
    F --> G[Database<br/>Update]:::db
    
    classDef app fill:#6983FF,stroke:#30176E,stroke-width:2px,color:#FFFDFA
    classDef cache fill:#D3DDE7,stroke:#30176E,stroke-width:2px,color:#1A2026
    classDef queue fill:#BCB5E7,stroke:#30176E,stroke-width:2px,color:#1A2026
    classDef success fill:#6983FF,stroke:#30176E,stroke-width:2px,color:#FFFDFA
    classDef worker fill:#E0A2AF,stroke:#642637,stroke-width:2px,color:#1A2026
    classDef db fill:#E0A2AF,stroke:#642637,stroke-width:2px,color:#1A2026
```

## Detailed Sequence

```mermaid
sequenceDiagram
    participant App as Application
    participant Cache as Valkey Cache
    participant Queue as Update Queue
    participant Worker as Background Worker
    participant DB as Database
    
    rect rgb(188, 181, 231)
    Note over App,Queue: Write-Behind Pattern (Fast Write)
    App->>Cache: 1. SET flight:123 [new_data] EX 3600
    Cache-->>App: ✓ OK (1ms)
    App->>Queue: 2. RPUSH update_queue [task]
    Queue-->>App: ✓ OK (1ms)
    App-->>App: Return success immediately ⚡
    Note over App: Total write time: ~2ms
    end
    
    rect rgb(211, 221, 231)
    Note over Worker,DB: Async Processing (Background)
    Worker->>Queue: 3. LPOP update_queue
    Queue-->>Worker: [task]
    Worker->>DB: 4. UPDATE flight SET departure = '10:00' WHERE id = 123
    DB-->>Worker: ✓ Success (50ms)
    Note over Worker: Processed in background
    end
    
    rect rgb(247, 251, 254)
    Note over App,DB: Subsequent Read
    App->>Cache: 5. GET flight:123
    Cache-->>App: [fresh data] (1ms) - From cache ⚡
    end
    
    Note over Cache,DB: Temporary inconsistency window until worker processes queue
```

## Implementation Pseudocode

```python
def update_data(id, new_value):
    """
    Write-Behind pattern in simple pseudocode
    """
    # Step 1: Write to cache immediately (fast!)
    cache_key = f"data:{id}"
    cache.set(cache_key, new_value, ttl=3600)
    
    # Step 2: Queue the database update for later
    task = {
        "id": id,
        "value": new_value,
        "timestamp": now()
    }
    queue.push(task)
    
    # Step 3: Return success immediately (don't wait for database)
    return success  # Total time: ~2ms


def background_worker():
    """
    Background worker that processes the queue
    Runs continuously in a separate process/thread
    """
    while True:
        # Get next task from queue
        task = queue.pop()
        
        if task exists:
            # Update database asynchronously
            database.update(task.id, task.value)
        
        sleep(100ms)  # Process queue every 100ms
```

### Real-World Example

```python
# Example: Updating flight departure time
flight_id = 123
new_departure = "10:00 AM"

# Write-Behind: Updates cache and queues database update
result = update_data(flight_id, new_departure)
# Returns in ~2ms (cache + queue time only)

# Immediate read gets data from cache
flight = get_data(flight_id)  # Returns updated time instantly

# Database update happens in background (50ms later)
# Background worker processes the queue asynchronously

# Another user reads the same data
flight = get_data(flight_id)  # Gets data from cache (consistent)

# Direct database query (bypassing cache) might show old data
# until background worker completes the update
```

## Comparison with Other Patterns

| Aspect | Write-Behind | Write-Through | Cache-Aside |
|--------|--------------|---------------|-------------|
| **Write Speed** | Fastest (~2ms) | Slower (~51ms) | Fast (~50ms) |
| **Consistency** | Eventual | Strong | Eventual |
| **Database Load** | Low (batched) | High (every write) | Medium |
| **Complexity** | High (needs workers) | Medium | Low |
| **Data Loss Risk** | Yes (if cache fails) | No | No |
| **Best For** | High-throughput writes | Strong consistency | Read-heavy loads |

## When to Use Write-Behind

✅ **Good For:**
- High-throughput write operations (analytics, logging, metrics)
- Applications that can tolerate eventual consistency
- Scenarios where write performance is critical
- Batch processing workloads
- Social media likes, view counts, activity feeds
- Gaming leaderboards and statistics

❌ **Not Ideal For:**
- Financial transactions requiring immediate consistency
- Critical data that cannot be lost
- Applications requiring strong consistency guarantees
- Scenarios where database must be immediately up-to-date
- Systems without infrastructure for background workers

## Handling Failures

Write-Behind requires careful consideration of failure scenarios:

- **Cache Failure**: Queued updates may be lost; consider persistent queues
- **Database Failure**: Implement retry logic with exponential backoff
- **Worker Failure**: Use multiple workers and health monitoring
- **Ordering**: Use timestamps or sequence numbers to ensure correct order
