# Write-Behind Cache Pattern

## Overview

The write-behind (write-back) cache pattern provides **fast writes** by updating the cache immediately and queuing database updates for asynchronous processing. This achieves **eventual consistency** with high write throughput.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ Write Request
       ▼
┌─────────────────────────────────────┐
│     WriteBehindCache                │
│  1. Update Cache (immediate)        │
│  2. Queue DB Update (async)         │
└──────┬──────────────────────────────┘
       │
       ├─────────────┬──────────────────┐
       │             │                  │
       ▼             ▼                  ▼
┌──────────┐  ┌──────────┐      ┌──────────┐
│  Cache   │  │  Queue   │      │ Database │
│ (Valkey) │  │ (Valkey  │      │ (MySQL)  │
│          │  │  List)   │      │          │
└──────────┘  └────┬─────┘      └────▲─────┘
                   │                  │
                   │  Background      │
                   │  Worker          │
                   └──────────────────┘
```

## Key Features

### 1. Fast Writes
- Updates complete at cache-speed (< 5ms typically)
- No waiting for database operations
- Ideal for high write throughput scenarios

### 2. Eventual Consistency
- Cache updated immediately
- Database updated asynchronously
- Temporary inconsistency window

### 3. Queue-Based Processing
- Updates queued in Valkey List (FIFO)
- Background worker processes queue in batches
- Automatic retry on failures (optional)

### 4. Audit Trail
- All changes logged in `flight_log` table
- Full history of updates with timestamps
- User attribution for changes

## Implementation

### Class: `WriteBehindCache`

Located in `daos/write_behind_cache.py`

#### Key Methods

**`get_flight(flight_id)`**
- Cache-aside read pattern
- Returns: `(flight_data, source, latency_ms, cache_key, query_str)`

**`update_flight_departure(flight_id, new_departure, new_arrival, user, comment)`**
- Write-behind update pattern
- Updates cache immediately
- Queues database update
- Returns: `(success, cache_key)`

**`process_queue(batch_size=10)`**
- Background worker method
- Processes queued updates in batches
- Returns: `(processed_count, failed_count, queries_executed)`

**`flush_queue()`**
- Process all pending updates
- Useful for testing and cleanup
- Returns: `total_processed`

**`get_queue_length()`**
- Check pending updates
- Returns: `queue_length`

**`verify_consistency(flight_id)`**
- Compare cache vs database
- Returns: `consistency_dict`

## Usage Examples

### Basic Usage

```python
from daos.write_behind_cache import WriteBehindCache
from datetime import datetime, timedelta

# Initialize
cache = WriteBehindCache()

# Read flight (cache-aside)
flight, source, latency, cache_key, query = cache.get_flight(115)

# Update flight (write-behind - fast!)
new_departure = datetime.now() + timedelta(hours=2)
new_arrival = datetime.now() + timedelta(hours=4)

success, cache_key = cache.update_flight_departure(
    flight_id=115,
    new_departure=new_departure,
    new_arrival=new_arrival,
    user="admin",
    comment="Flight delayed"
)

# Check queue
queue_length = cache.get_queue_length()
print(f"Pending updates: {queue_length}")

# Process queue (background worker)
processed, failed, queries = cache.process_queue(batch_size=10)
print(f"Processed: {processed}, Failed: {failed}")

# Cleanup
cache.close()
```

### Background Worker Pattern

```python
import time
from daos.write_behind_cache import WriteBehindCache

def background_worker(interval_seconds=5):
    """Background worker to process queue periodically"""
    cache = WriteBehindCache()
    
    try:
        while True:
            queue_length = cache.get_queue_length()
            
            if queue_length > 0:
                processed, failed, _ = cache.process_queue(batch_size=100)
                print(f"Processed {processed} updates, {failed} failed")
            
            time.sleep(interval_seconds)
    finally:
        cache.close()

# Run in separate thread or process
import threading
worker_thread = threading.Thread(target=background_worker, daemon=True)
worker_thread.start()
```

## Demo Script

### Running the Demo

```bash
# Basic demo
python samples/demo_write_behind_cache.py run

# Interactive mode (step-by-step)
python samples/demo_write_behind_cache.py run --interactive

# Verbose mode (show SQL queries)
python samples/demo_write_behind_cache.py run --verbose

# Flush cache/queue before demo
python samples/demo_write_behind_cache.py run --flush

# Custom flight ID
python samples/demo_write_behind_cache.py run --flight-id 200

# Combined flags
python samples/demo_write_behind_cache.py run -i -v -f --flight-id 115
```

### Demo Steps

1. **Initial Read** - Cache-aside pattern (CACHE_MISS)
2. **Cached Read** - Cache hit demonstration
3. **Write-Behind Update** - Fast cache update + queue
4. **Consistency Check (Before)** - Show inconsistency
5. **Process Queue** - Background worker simulation
6. **Consistency Check (After)** - Show consistency
7. **Read Updated Data** - Verify cache has new data
8. **Restore Original** - Cleanup (flush queue)
9. **Summary** - Key takeaways and comparison

## Performance Characteristics

### Write Performance

| Pattern | Typical Latency | Consistency |
|---------|----------------|-------------|
| Write-Through | 50-200ms | Immediate |
| Write-Behind | 1-5ms | Eventual |

### Write-Behind Advantages
- **10-50x faster writes** compared to write-through
- High throughput for write-heavy workloads
- Reduced database load through batching

### Trade-offs
- Temporary inconsistency window
- Requires background worker
- More complex error handling
- Risk of data loss if cache fails before queue processing

## When to Use

### ✅ Good For:
- High write throughput requirements
- Write-heavy workloads
- Non-critical data updates
- Scenarios where eventual consistency is acceptable
- Batch processing opportunities

### ❌ Not Good For:
- Financial transactions
- Critical data requiring immediate consistency
- Scenarios where data loss is unacceptable
- Simple applications (overhead not justified)

## Pattern Comparison

| Aspect | Cache-Aside | Write-Through | Write-Behind |
|--------|-------------|---------------|--------------|
| Read Performance | Fast (cached) | Fast (cached) | Fast (cached) |
| Write Performance | Fast (DB only) | Slow (DB + Cache) | **Very Fast (cache only)** |
| Consistency | May be stale | Immediate | Eventual |
| Complexity | Simple | Medium | **High** |
| Use Case | Read-heavy | Consistency critical | **Write-heavy** |

## Configuration

### Environment Variables

```bash
# Database configuration
DB_ENGINE=mysql  # or postgresql, mariadb
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flughafendb
DB_USER=root
DB_PASSWORD=password

# Cache configuration
CACHE_ENGINE=valkey  # or redis, memcached
CACHE_HOST=localhost
CACHE_PORT=6379
CACHE_TTL=3600  # seconds

# Queue configuration (optional)
QUEUE_BATCH_SIZE=10
QUEUE_PROCESS_INTERVAL=5  # seconds
```

## Error Handling

### Failed Updates
- Failed updates can be re-queued (optional)
- Implement retry logic with exponential backoff
- Log failures for manual intervention

### Cache Failures
- Queue persists in Valkey (durable)
- Can recover and process after cache restart
- Consider dead-letter queue for persistent failures

## Monitoring

### Key Metrics
- Queue length (pending updates)
- Processing rate (updates/second)
- Failure rate
- Consistency lag (time to consistency)
- Write latency

### Health Checks
```python
# Check queue health
queue_length = cache.get_queue_length()
if queue_length > 1000:
    alert("Queue backlog detected")

# Check consistency
consistency = cache.verify_consistency(flight_id)
if not consistency["consistent"]:
    log("Inconsistency detected", consistency)
```

## Best Practices

1. **Background Worker**: Run as separate process/thread
2. **Batch Processing**: Process queue in batches for efficiency
3. **Monitoring**: Track queue length and processing rate
4. **Error Handling**: Implement retry logic for failed updates
5. **Graceful Shutdown**: Flush queue before shutdown
6. **Testing**: Test failure scenarios (cache down, DB down)
7. **Documentation**: Document consistency guarantees

## Related Patterns

- **Cache-Aside**: Read pattern used by write-behind
- **Write-Through**: Alternative with immediate consistency
- **Event Sourcing**: Similar queue-based approach
- **CQRS**: Separate read/write models

## References

- [Cache-Aside Pattern](./CACHE_ASIDE_README.md)
- [Write-Through Pattern](./WRITE_THROUGH_CACHE_README.md)
- [Caching Patterns Comparison](./CACHING_PATTERNS_COMPARISON.md)
