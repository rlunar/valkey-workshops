# SQL Query Samples for Flughafen Airport Database

This directory contains example SQL queries organized by complexity level, demonstrating various database operations on the airport database schema.

## Files Overview

### 01_simple_queries.sql
**Single table operations** - Basic SELECT statements with simple filtering.

Examples:
- Fetch airline by ID or IATA code
- Get airport by ICAO/IATA code
- Find airports by name pattern
- Count passengers and bookings
- Get employee by username

**Use cases:** Quick lookups, data validation, simple reports

---

### 02_medium_queries.sql
**Joins and filtering** - Queries involving 2-3 table joins with filtering.

Examples:
- Get passenger with their details (passenger + passengerdetails)
- Find passengers by country and/or passport
- Get flights with airline information
- Get flights between specific airports
- Count bookings per passenger
- Get airplane with type information

**Use cases:** User profiles, search functionality, basic analytics

---

### 03_advanced_queries.sql
**Complex joins and aggregations** - Multi-table joins (4+ tables) with analytics.

Key queries:

1. **Last 10 Passenger Bookings** - Complete booking history with:
   - Passenger information
   - Flight details (number, departure, arrival)
   - Departure airport (name, IATA code)
   - Arrival airport (name, IATA code)
   - Airline information

2. **Passenger's Complete Booking History** - All bookings for a specific passenger

3. **Upcoming Flights** - Future flights with passenger, airport, and airplane details

4. **Flight Manifest** - All passengers on a specific flight with seat assignments

5. **Revenue Analysis by Route** - Top routes by revenue with statistics

6. **Passenger Travel Statistics** - Frequent flyers with spending patterns

7. **Detailed Flight Information** - Complete flight data including:
   - Duration calculation
   - Geographic information (cities, countries)
   - Seat availability
   - Airplane type and capacity

8. **Busiest Routes** - Routes ranked by passenger count

9. **Airline Performance Summary** - Fleet size, revenue, and efficiency metrics

10. **Recent Bookings with Geography** - Latest bookings with full geographic context

**Use cases:** Business intelligence, reporting dashboards, customer analytics, operational insights

---

## Query Complexity Comparison

| Level | Tables Joined | Aggregations | Subqueries | Use Case |
|-------|--------------|--------------|------------|----------|
| Simple | 1 | None | None | Lookups, validation |
| Medium | 2-3 | Basic (COUNT) | None | Search, profiles |
| Advanced | 4+ | Multiple (SUM, AVG, COUNT) | Optional | Analytics, BI |

## Performance Considerations

### Indexed Columns (from schema)
- `airport.iata`, `airport.icao`, `airport.name`
- `airline.iata`, `airline.base_airport`
- `flight.from`, `flight.to`, `flight.departure`, `flight.arrival`
- `booking.flight_id`, `booking.passenger_id`
- `passenger.passportno`

### Tips for Production Use
1. Always use `LIMIT` for exploratory queries
2. Add indexes on frequently filtered columns
3. Use `EXPLAIN` to analyze query performance
4. Consider caching results for expensive aggregations
5. Use prepared statements to prevent SQL injection

## Testing Queries

Replace placeholder values:
- `passenger_id = 1000` → Use actual passenger ID
- `flight_id = 115` → Use actual flight ID
- `airline_id = 1` → Use actual airline ID
- `'JFK'`, `'FRA'` → Use actual airport codes

## Python Demos

### cache_aside_demo.py
**Cache-Aside (Lazy Loading) Pattern** - Demonstrates read-heavy caching strategy.

Features:
- Cache miss → Database query → Store in cache
- Cache hit → Return cached data (fast)
- Manual cache invalidation
- Force refresh capability

**Use cases:** Read-heavy workloads, data that changes infrequently

See: [Cache-Aside Documentation](../docs/CACHE_ASIDE_README.md)

---

### write_through_cache_demo.py
**Write-Through Cache Pattern** - Demonstrates data consistency for updates.

Features:
- Simultaneous database and cache updates
- Flight departure time updates
- Audit logging to `flight_log` table
- Consistency verification between DB and cache
- Automatic cleanup (restores original data)

**Use cases:** Critical data updates (flight status, inventory, pricing)

See: [Write-Through Cache Documentation](../docs/WRITE_THROUGH_CACHE_README.md)

**Demo flow:**
1. Initial read (cache miss)
2. Second read (cache hit)
3. Update flight times (write-through)
4. Verify consistency
5. Read updated data
6. Restore original times

---

### nlp_to_sql.py
**Natural Language to SQL** - Convert English questions to SQL queries.

See: [NLP to SQL Documentation](../docs/nlp_to_sql_README.md)

---

### semantic_search.py
**Semantic Search** - Find relevant database entities using embeddings.

See: [Semantic Search Documentation](../docs/semantic_search_README.md)

---

### demo_stampede_prevention.py
**Stampede Prevention Demo** - Demonstrates distributed locking to prevent cache stampede.

Features:
- Simulates concurrent requests to the same resource
- Distributed locking with Redis/Valkey
- Exponential backoff for lock contention
- Fail-fast behavior with timeouts
- Detailed metrics per thread
- Request timeline visualization

**Key concepts:**
- **Cache Stampede**: Multiple concurrent requests for the same missing cache entry
- **Distributed Lock**: Only one thread fetches from API, others wait
- **Exponential Backoff**: Reduces contention with increasing delays
- **Lock Timeout**: Prevents indefinite waiting

**Usage examples:**
```bash
# Basic test: 10 concurrent threads, 3 cities
uv run samples/demo_stampede_prevention.py

# High concurrency test
uv run samples/demo_stampede_prevention.py --threads 20 --cities 5

# Verbose mode with thread-level details
uv run samples/demo_stampede_prevention.py --verbose --threads 15

# Interactive mode with step-by-step execution
uv run samples/demo_stampede_prevention.py --interactive --verbose

# Flush cache before running
uv run samples/demo_stampede_prevention.py --flush --threads 10
```

**Metrics captured:**
- Total requests vs API calls (should be 1:N ratio)
- Cache hit/miss rates
- Lock acquisitions and waits
- Average wait time for lock contention
- Request timeline with status per thread
- Stampede prevention success rate

**Use cases:**
- High-traffic scenarios (major cities, popular products)
- Preventing API rate limit exhaustion
- Cost optimization (reducing unnecessary API calls)
- System stability under concurrent load
- Demonstrating distributed locking patterns

---

### multi_threaded_performance_test.py
**Multi-threaded Performance Testing** - Benchmark database and cache performance under concurrent load.

Features:
- Simulates multiple concurrent users (threads)
- Configurable read/write ratio
- Cache-aside pattern implementation
- Detailed metrics collection per second
- JSON log output with comprehensive statistics
- SSL/TLS support for Valkey connections

**Metrics captured:**
- Total queries and queries per second
- Read/write operation breakdown
- Cache hit/miss rates
- Min/max/average query times
- Time-series data for performance analysis

**Usage examples:**
```bash
# Basic test: 4 users, 10 queries each, 80% reads
python samples/multi_threaded_performance_test.py

# High concurrency test
python samples/multi_threaded_performance_test.py --users 20 --queries 100

# Write-heavy workload with SSL
python samples/multi_threaded_performance_test.py --users 10 --queries 50 --read_rate 30 --ssl true

# Custom log tag for test identification
python samples/multi_threaded_performance_test.py --users 8 --queries 200 --log_tag prod_baseline
```

**Output:**
- Console: Real-time summary with operation counts and cache performance
- JSON log: Detailed metrics in `logs/perf_test_TIMESTAMP_TAG.json`

**Use cases:** 
- Performance benchmarking
- Capacity planning
- Cache effectiveness analysis
- Load testing before production deployment
- Comparing different cache configurations

---

## Integration with Cache Systems

These queries are ideal candidates for caching:
- **Simple queries**: Cache for 1 hour (rarely change)
- **Medium queries**: Cache for 15-30 minutes
- **Advanced queries**: Cache for 5-10 minutes (or invalidate on booking)

### Caching Patterns

| Pattern | Best For | Demo |
|---------|----------|------|
| Cache-Aside | Read-heavy workloads | `cache_aside_demo.py` |
| Write-Through | Critical updates requiring consistency | `write_through_cache_demo.py` |
| Write-Behind | High-throughput writes | (Not implemented) |

See `airport_app.py` for cache-aside pattern implementation.
