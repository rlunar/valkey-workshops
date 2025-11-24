# Caching Patterns Comparison

## Overview

This document compares different caching patterns implemented in the airport database project, helping you choose the right pattern for your use case.

## Pattern Summary

| Pattern | Read Path | Write Path | Consistency | Complexity |
|---------|-----------|------------|-------------|------------|
| **Cache-Aside** | Cache → DB → Cache | DB → Invalidate | Eventual | Low |
| **Write-Through** | Cache → DB → Cache | DB → Cache | Strong | Medium |
| **Write-Behind** | Cache → DB → Cache | Cache → DB (async) | Eventual | High |

## Cache-Aside (Lazy Loading)

### How It Works

**Read:**
```
1. Check cache
2. If HIT → return cached data
3. If MISS → query database
4. Store result in cache
5. Return data
```

**Write:**
```
1. Update database
2. Invalidate cache entry
3. Next read will be cache miss
```

### Pros
- ✅ Simple to implement
- ✅ Only caches data that's actually read
- ✅ Cache failures don't affect writes
- ✅ Good for read-heavy workloads

### Cons
- ❌ First read after write is slow (cache miss)
- ❌ Risk of stale data if invalidation fails
- ❌ Cache stampede on popular items

### Best For
- Read-heavy workloads (90%+ reads)
- Data that changes infrequently
- Non-critical data where eventual consistency is acceptable

### Example Use Cases
- Airline information (rarely changes)
- Airport details (static data)
- Airplane types (reference data)
- Historical flight data

### Demo
```bash
python samples/cache_aside_demo.py
```

See: [Cache-Aside Documentation](./CACHE_ASIDE_README.md)

---

## Write-Through Cache

### How It Works

**Read:**
```
1. Check cache
2. If HIT → return cached data
3. If MISS → query database
4. Store result in cache
5. Return data
```

**Write:**
```
1. Update database (source of truth)
2. Immediately update cache
3. Both DB and cache now consistent
```

### Pros
- ✅ Strong consistency (cache always matches DB)
- ✅ No stale data
- ✅ Predictable read performance
- ✅ Simplified invalidation logic

### Cons
- ❌ Slower writes (DB + cache)
- ❌ Cache overhead for infrequently read data
- ❌ More complex implementation

### Best For
- Critical data requiring consistency
- Frequent reads after writes
- Data where staleness is unacceptable

### Example Use Cases
- **Flight status updates** (departure delays, gate changes)
- **Booking confirmations** (seat assignments)
- **Inventory levels** (available seats)
- **Pricing updates** (ticket prices)
- **User profiles** (critical user data)

### Demo
```bash
python samples/write_through_cache_demo.py
```

See: [Write-Through Cache Documentation](./WRITE_THROUGH_CACHE_README.md)

---

## Write-Behind (Write-Back)

### How It Works

**Read:**
```
1. Check cache
2. If HIT → return cached data
3. If MISS → query database
4. Store result in cache
5. Return data
```

**Write:**
```
1. Update cache immediately
2. Return success to client
3. Asynchronously write to database (batched)
```

### Pros
- ✅ Fastest write performance
- ✅ Can batch multiple writes
- ✅ Reduces database load
- ✅ Good for write-heavy workloads

### Cons
- ❌ Risk of data loss if cache fails
- ❌ Complex implementation
- ❌ Eventual consistency
- ❌ Difficult to debug

### Best For
- Write-heavy workloads
- High-throughput scenarios
- Non-critical data
- Analytics/logging data

### Example Use Cases
- Session data
- Analytics events
- Log aggregation
- Metrics collection

### Status
⚠️ Not implemented in this project (high complexity)

---

## Decision Matrix

### Choose Cache-Aside When:
- ✅ Reads >> Writes (90%+ reads)
- ✅ Data changes infrequently
- ✅ Eventual consistency is acceptable
- ✅ Simple implementation preferred
- ✅ Cache failures shouldn't block writes

**Examples:** Airline info, airport details, airplane types

---

### Choose Write-Through When:
- ✅ Data consistency is critical
- ✅ Reads are frequent after writes
- ✅ Stale data is unacceptable
- ✅ Audit trail required
- ✅ Predictable performance needed

**Examples:** Flight status, bookings, inventory, pricing

---

### Choose Write-Behind When:
- ✅ Writes >> Reads (write-heavy)
- ✅ High throughput required
- ✅ Eventual consistency acceptable
- ✅ Data loss risk is manageable
- ✅ Complex infrastructure available

**Examples:** Analytics, logs, metrics, session data

---

## Real-World Scenarios

### Scenario 1: Flight Search
**Pattern:** Cache-Aside  
**Reason:** Read-heavy, data changes infrequently, eventual consistency OK

```python
# User searches for flights from JFK to LAX
flights = cache.execute_query("""
    SELECT * FROM flight 
    WHERE from = (SELECT airport_id FROM airport WHERE iata = 'JFK')
    AND to = (SELECT airport_id FROM airport WHERE iata = 'LAX')
    AND departure > NOW()
""")
```

### Scenario 2: Flight Delay Update
**Pattern:** Write-Through  
**Reason:** Critical update, passengers need accurate info immediately

```python
# Flight LH400 delayed by 2 hours
cache.update_flight_departure(
    flight_id=1,
    new_departure=original_time + timedelta(hours=2),
    new_arrival=original_arrival + timedelta(hours=2),
    comment="Weather delay"
)
# Database and cache both updated immediately
```

### Scenario 3: Booking Confirmation
**Pattern:** Write-Through  
**Reason:** Critical transaction, must be consistent

```python
# User books seat 12A on flight 115
with transaction:
    db.insert_booking(passenger_id, flight_id, seat)
    cache.update_flight_availability(flight_id)
# Both DB and cache updated atomically
```

### Scenario 4: Analytics Event
**Pattern:** Write-Behind (if implemented)  
**Reason:** High volume, eventual consistency OK

```python
# Track search event
cache.log_event({
    "type": "search",
    "user_id": 12345,
    "query": "JFK to LAX",
    "timestamp": now()
})
# Written to cache, batched to DB later
```

---

## Performance Comparison

### Read Performance

| Pattern | Cache Hit | Cache Miss | Notes |
|---------|-----------|------------|-------|
| Cache-Aside | ~1ms | ~50ms | Standard |
| Write-Through | ~1ms | ~50ms | Same as cache-aside |
| Write-Behind | ~1ms | ~50ms | Same as cache-aside |

### Write Performance

| Pattern | Latency | Consistency | Notes |
|---------|---------|-------------|-------|
| Cache-Aside | ~50ms | Eventual | DB write only |
| Write-Through | ~55ms | Strong | DB + cache write |
| Write-Behind | ~1ms | Eventual | Cache write only |

---

## Implementation Checklist

### Cache-Aside
- [ ] Implement cache key generation
- [ ] Handle cache misses
- [ ] Implement cache invalidation
- [ ] Set appropriate TTL values
- [ ] Handle cache failures gracefully

### Write-Through
- [ ] All of Cache-Aside, plus:
- [ ] Implement atomic DB + cache updates
- [ ] Add audit logging
- [ ] Implement consistency verification
- [ ] Handle partial failures
- [ ] Add retry logic

### Write-Behind
- [ ] All of Cache-Aside, plus:
- [ ] Implement async write queue
- [ ] Add batch processing
- [ ] Handle queue failures
- [ ] Implement data recovery
- [ ] Add monitoring and alerting

---

## Monitoring Recommendations

### Key Metrics

1. **Cache Hit Rate**
   - Target: >80% for cache-aside
   - Target: >90% for write-through

2. **Cache Latency**
   - Target: <5ms for reads
   - Target: <10ms for writes

3. **Consistency Lag** (write-through)
   - Target: <100ms between DB and cache

4. **Write Queue Depth** (write-behind)
   - Target: <1000 pending writes

### Alerts

- Cache hit rate drops below 70%
- Cache latency exceeds 50ms
- Consistency check failures
- Write queue backlog growing

---

## Migration Guide

### From Cache-Aside to Write-Through

1. Identify critical data requiring strong consistency
2. Implement write-through update methods
3. Add consistency verification
4. Deploy with feature flag
5. Monitor consistency metrics
6. Gradually migrate traffic

### From Write-Through to Cache-Aside

1. Identify data where eventual consistency is acceptable
2. Remove cache updates from write path
3. Add cache invalidation
4. Update TTL values
5. Monitor cache hit rates

---

## References

- [Cache-Aside Demo](../samples/cache_aside_demo.py)
- [Write-Through Demo](../samples/write_through_cache_demo.py)
- [Cache-Aside Documentation](./CACHE_ASIDE_README.md)
- [Write-Through Documentation](./WRITE_THROUGH_CACHE_README.md)

---

## Quick Reference

```python
# Cache-Aside: Read
data = cache.get(key)
if not data:
    data = db.query()
    cache.set(key, data)

# Cache-Aside: Write
db.update(data)
cache.delete(key)  # Invalidate

# Write-Through: Write
db.update(data)
cache.set(key, data)  # Update immediately

# Write-Behind: Write
cache.set(key, data)
queue.add(lambda: db.update(data))  # Async
```
