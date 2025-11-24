# Write-Through Cache Pattern

## Overview

The **Write-Through Cache** pattern ensures data consistency by writing updates to both the database (source of truth) and the cache simultaneously. This is critical for scenarios where data accuracy is paramount, such as flight status updates.

## Pattern Comparison

### Cache-Aside (Lazy Loading)
- **Read**: Check cache → if miss, read from DB → store in cache
- **Write**: Update DB → invalidate cache
- **Risk**: Stale data between DB update and cache invalidation

### Write-Through
- **Read**: Check cache → if miss, read from DB → store in cache
- **Write**: Update DB → immediately update cache
- **Benefit**: Cache always reflects latest DB state

## Demo: Flight Status Update

The `write_through_cache_demo.py` demonstrates data consistency when updating flight departure/arrival times.

### Key Features

1. **Atomic Updates**: Database and cache are updated in sequence within a transaction
2. **Audit Logging**: All changes are logged to `flight_log` table
3. **Consistency Verification**: Built-in checks to verify DB and cache match
4. **Automatic Rollback**: If cache update fails, the demo can detect inconsistency

### Demo Flow

```
[STEP 1] Initial Read (Cache Miss)
   ✗ Cache MISS for flight 1
   → Reads from database
   → Stores in cache

[STEP 2] Second Read (Cache Hit)
   ✓ Cache HIT for flight 1
   → Returns cached data (faster)

[STEP 3] Update Flight Times (Write-Through)
   → Updates database (source of truth)
   → Logs change to flight_log
   → Immediately updates cache
   ✓ Database and cache now consistent

[STEP 4] Verify Consistency
   → Reads from both database and cache
   → Compares departure/arrival times
   ✓ Data is CONSISTENT

[STEP 5] Read Updated Data
   ✓ Cache HIT for flight 1
   → Returns updated data from cache

[STEP 6] Restore Original Times
   → Cleans up demo changes
   → Uses write-through pattern again
```

## Running the Demo

### Prerequisites

1. Database running with `flughafendb_large` schema
2. Cache server running (Redis/Valkey/Memcached)
3. Environment variables configured in `.env`

### Required Environment Variables

```bash
# Database Configuration
DB_ENGINE=mysql          # or mariadb, postgresql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=flughafendb_large

# Cache Configuration
CACHE_ENGINE=redis       # or valkey, memcached
CACHE_HOST=localhost
CACHE_PORT=6379
CACHE_TTL=3600          # 1 hour
```

### Execute Demo

```bash
# From project root
python samples/write_through_cache_demo.py
```

### Expected Output

```
============================================================
WRITE-THROUGH CACHE PATTERN DEMO
Demonstrating Data Consistency for Flight Updates
============================================================

[STEP 1] Initial read - Cache-Aside Pattern
------------------------------------------------------------
   ✗ Cache MISS for flight 1

Initial Flight Data
------------------------------------------------------------
Flight ID:    1
Flight No:    LH400
Route:        FRA → JFK
Airline:      Lufthansa
Departure:    2025-11-20T10:00:00
Arrival:      2025-11-20T18:30:00

[STEP 2] Second read - Should hit cache
------------------------------------------------------------
   ✓ Cache HIT for flight 1

[STEP 3] Update flight departure time - Write-Through Pattern
------------------------------------------------------------
Updating flight 1:
  Old departure: 2025-11-20 10:00:00
  New departure: 2025-11-20 12:00:00
  Old arrival:   2025-11-20 18:30:00
  New arrival:   2025-11-20 20:30:00

   ✓ Database updated for flight 1
   ✗ Cache MISS for flight 1
   ✓ Cache updated for flight 1

✓ Write-through update completed successfully

[STEP 4] Verify data consistency
------------------------------------------------------------
✓ Data is CONSISTENT between database and cache

[STEP 5] Read updated flight data
------------------------------------------------------------
   ✓ Cache HIT for flight 1

[STEP 6] Restore original flight times
------------------------------------------------------------
Restoring original departure and arrival times...
   ✓ Database updated for flight 1
   ✗ Cache MISS for flight 1
   ✓ Cache updated for flight 1

✓ Original times restored
```

## Implementation Details

### WriteThroughCache Class

```python
class WriteThroughCache:
    def update_flight_departure(
        self, 
        flight_id: int, 
        new_departure: datetime,
        new_arrival: datetime,
        user: str = "system",
        comment: Optional[str] = None
    ) -> bool:
        """
        Write-through pattern implementation:
        1. Update database (within transaction)
        2. Log change to flight_log
        3. Immediately update cache
        """
```

### Key Methods

- `get_flight(flight_id)`: Cache-aside read pattern
- `update_flight_departure(...)`: Write-through update pattern
- `verify_consistency(flight_id)`: Checks DB vs cache consistency

## Benefits of Write-Through

1. **Strong Consistency**: Cache always reflects database state
2. **Simplified Logic**: No need for complex invalidation strategies
3. **Audit Trail**: All changes logged to `flight_log`
4. **Predictable Behavior**: Reads always return latest data

## Trade-offs

1. **Write Latency**: Slightly slower writes (DB + cache)
2. **Cache Overhead**: Every write updates cache (even if not read)
3. **Complexity**: More code than simple cache invalidation

## When to Use Write-Through

✅ **Use when:**
- Data consistency is critical (flight status, inventory, pricing)
- Reads are frequent after writes
- Stale data is unacceptable

❌ **Avoid when:**
- Write-heavy workloads with infrequent reads
- Cache misses are acceptable
- Eventual consistency is sufficient

## Real-World Use Cases

1. **Flight Status Updates**: Departure delays, gate changes, cancellations
2. **Inventory Management**: Stock levels, product availability
3. **Pricing Systems**: Real-time price updates
4. **Booking Systems**: Seat availability, reservation status
5. **User Profiles**: Critical user data that must be consistent

## Monitoring and Debugging

### Check Cache Contents

```bash
# Redis/Valkey
redis-cli GET "flight:1"

# Memcached
echo "get flight:1" | nc localhost 11211
```

### Verify Database

```sql
-- Check flight data
SELECT * FROM flight WHERE flight_id = 1;

-- Check audit log
SELECT * FROM flight_log 
WHERE flight_id = 1 
ORDER BY log_date DESC 
LIMIT 5;
```

### Consistency Check

The demo includes a `verify_consistency()` method that compares database and cache:

```python
consistency = cache.verify_consistency(flight_id)
if consistency["consistent"]:
    print("✓ Data is consistent")
else:
    print("✗ Inconsistency detected!")
    print(f"Reason: {consistency['reason']}")
```

## Advanced Scenarios

### Handling Cache Failures

If cache update fails after database update, you have options:

1. **Retry**: Attempt cache update again
2. **Log**: Record inconsistency for monitoring
3. **Invalidate**: Remove stale cache entry
4. **Alert**: Notify operations team

### Distributed Systems

In distributed environments, consider:

1. **Two-Phase Commit**: Ensure atomicity across DB and cache
2. **Event Sourcing**: Publish events for cache updates
3. **CDC (Change Data Capture)**: Automatically sync cache from DB changes

## Related Patterns

- **Cache-Aside**: Read-heavy workloads (see `cache_aside_demo.py`)
- **Write-Behind**: Async writes for high throughput
- **Refresh-Ahead**: Proactive cache warming

## References

- [Cache-Aside Pattern Documentation](./CACHE_ASIDE_README.md)
- [Flight Schema](../knowledge_base/flight.json)
- [Flight Log Schema](../knowledge_base/flight_log.json)

## Support

For questions or issues:
1. Check environment variables in `.env`
2. Verify database and cache connectivity
3. Review logs for error messages
4. Ensure flight_id exists in database
