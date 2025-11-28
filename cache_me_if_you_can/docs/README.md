# Cache Me If You Can - Documentation

## Project Overview

This project demonstrates various **caching patterns** using Valkey/Redis with a realistic airport database (Flughafen). It showcases how caching can dramatically improve application performance while maintaining data consistency.

This hands-on workshop explores practical caching with Valkey through three key use cases: database query optimization, session management, and real-time leaderboards. You'll learn to cache expensive database operations, external API calls, and JSON configurations while building scalable session storage and dynamic leaderboards.

### What You'll Learn

- **Cache-Aside Pattern**: Lazy loading with automatic cache population
- **Write-Through Pattern**: Maintaining cache consistency during updates
- **Write-Behind Pattern**: Asynchronous writes with queue processing
- **Semantic Search**: Using vector embeddings for intelligent query caching
- **NLP to SQL**: Converting natural language to SQL queries with caching
- **Stampede Prevention**: Distributed locking to prevent cache stampede
- **Performance Testing**: Multi-threaded load testing and analysis

### Technology Stack

- **Databases**: MySQL, MariaDB, or PostgreSQL
- **Cache**: Valkey or Redis
- **Vector Search**: Sentence Transformers for embeddings
- **NLP**: Ollama for natural language processing

---

## Quick Start

### Prerequisites

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set up your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your database and cache credentials
   ```

3. Load the airport database (see `data/` folder)

4. Ensure Valkey/Redis is running:
   ```bash
   # Check if Valkey is running
   redis-cli ping
   # Should return: PONG
   ```

---

## Workshop Flow: Step-by-Step Guide

Follow this structured approach to learn caching patterns progressively. Each module builds on the previous one.

### Run All Demos Automatically

To run all demos in sequence with automatic visualization:

```bash
# Run all demos with default settings
python scripts/run_all_demos.py

# List all available demos
python scripts/run_all_demos.py --list

# Run without pausing between demos
python scripts/run_all_demos.py --skip-prompts

# Run with verbose output
python scripts/run_all_demos.py --verbose

# Run in interactive mode with detailed explanations
python scripts/run_all_demos.py --interactive --verbose
```

### Or Follow the Workshop Modules Below

---

## Module 1: Why Caching is Important?

### 1.1 Explore the Airport Application

Start by understanding the sample application and seeing caching benefits visually.

```bash
# Launch the Airport App (Streamlit UI)
uv run streamlit run airport_app.py
```

**What to explore:**
- Browse airports, flights, and airlines
- Notice query latency without caching
- Enable caching and observe performance improvements
- Compare cache hits vs. cache misses

### 1.2 Understand the AirportDB Schema

Explore the database schema and run sample queries to understand latency.

```bash
# Connect to your database using mycli
mycli -h localhost -u your_user -p your_password flughafendb

# Run sample queries and check execution time
SELECT * FROM airport WHERE iata_code = 'JFK';

# Use EXPLAIN to understand query plans
EXPLAIN SELECT * FROM flight f 
JOIN airport a ON f.from = a.airport_id 
WHERE a.iata_code = 'JFK';
```

**Schema files:**
- `docs/flughafendb_schema_en.sql` - Full schema definition
- `docs/bug_fixes_flughafendb_large.sql` - Schema fixes

---

## Module 2: Common Caching Patterns

Learn the three fundamental caching patterns with hands-on demos.

### 2.1 Cache-Aside (Lazy Loading)

Load data into cache only when requested. Data is fetched from the database on cache miss.

```bash
# Run the demo
uv run samples/demo_cache_aside.py

# With verbose output
uv run samples/demo_cache_aside.py --verbose

# Interactive mode (step-by-step)
uv run samples/demo_cache_aside.py --interactive
```

**What it demonstrates:**
- Simple queries (single table lookups)
- Medium queries (2-3 table joins)
- Complex queries (4+ table joins with aggregations)
- Performance comparison: cache hit vs. cache miss
- Latency improvements (typically 10-100x faster)

**Key concepts:**
- ✅ Memory efficient - only caches requested data
- ✅ Simple to implement
- ✅ Resilient to cache failures
- ⚠️ Initial request is always slow (cache miss)
- ⚠️ Potential for stale data

**Learn more:** [concepts/cache_aside.md](concepts/cache_aside.md)

---

### 2.2 Write-Through Cache

Write to cache and database simultaneously to maintain strong consistency.

```bash
# Run the demo
uv run samples/demo_write_through_cache.py

# With verbose output
uv run samples/demo_write_through_cache.py --verbose

# Interactive mode
uv run samples/demo_write_through_cache.py --interactive
```

**What it demonstrates:**
- Updating flight departure times
- Simultaneous database and cache updates
- Consistency verification between DB and cache
- Audit logging for all changes

**Key concepts:**
- ✅ Strong consistency - cache and DB always in sync
- ✅ No stale data
- ✅ Predictable behavior
- ⚠️ Slower writes (must update both systems)
- ⚠️ Write amplification

**Learn more:** [concepts/write_through_cache.md](concepts/write_through_cache.md)

---

### 2.3 Write-Behind (Write-Back) Cache

Write to cache immediately, database asynchronously for maximum performance.

```bash
# Run the demo
uv run samples/demo_write_behind_cache.py

# With verbose output
uv run samples/demo_write_behind_cache.py --verbose

# Interactive mode
uv run samples/demo_write_behind_cache.py --interactive
```

**What it demonstrates:**
- Fast writes to cache (returns immediately)
- Asynchronous database updates via queue
- Queue monitoring and batch processing
- Background worker processing

**Key concepts:**
- ✅ Maximum write performance (~2ms)
- ✅ High throughput
- ✅ Reduced database load
- ⚠️ Eventual consistency
- ⚠️ Risk of data loss if cache fails

**Learn more:** [concepts/write_behind_cache.md](concepts/write_behind_cache.md)

---

## Module 3: Anything That Can Be Queried Can Be Cached

Learn how to cache external APIs and AI model responses.

### 3.1 Weather API Caching

Use Valkey to cache external API responses, reducing latency and costs.

```bash
# Run the demo with 5 cities
uv run samples/demo_weather_api_cache.py --cities 5

# With verbose output and custom TTL
uv run samples/demo_weather_api_cache.py --cities 10 --ttl 300 --verbose

# Interactive mode
uv run samples/demo_weather_api_cache.py --interactive
```

**What it demonstrates:**
- Caching third-party API responses
- TTL-based expiration for weather data
- Country flags 🇺🇸 🇲🇽 🇬🇧 and weather emojis ☀️ 🌧️ ⛅
- Syntax-highlighted JSON output
- Reducing API costs and latency

**Key metrics:**
- First request: ~500ms (API call)
- Cached request: ~1ms (500x faster!)
- Cost savings: 99%+ for repeated requests

---

### 3.2 GenAI Semantic Caching

Use Valkey Vector Similarity Search to cache AI model responses for similar prompts.

```bash
# Run the semantic cache demo
uv run samples/demo_semantic_cache.py

# With verbose output
uv run samples/demo_semantic_cache.py --verbose

# Interactive mode
uv run samples/demo_semantic_cache.py --interactive
```

**What it demonstrates:**
- Converting natural language to SQL using AI
- Vector embeddings for semantic similarity
- Reusing cached results for similar questions
- Token savings and latency reduction
- Vector index management in Valkey

**Example:**
- Query 1: "flights from Berlin to Munich"
- Query 2: "show flights between Berlin and Munich"
- Result: Query 2 hits semantic cache! (90%+ similarity)

**Key metrics:**
- Without cache: 2000-5000ms + LLM tokens
- With semantic cache: 1-3ms, 0 tokens (1000x+ faster!)

**Learn more:** 
- [SEMANTIC_SEARCH_DEMO_EXPLAINED.md](SEMANTIC_SEARCH_DEMO_EXPLAINED.md)
- [SEMANTIC_SEARCH_SUMMARY.md](SEMANTIC_SEARCH_SUMMARY.md)

**NLP to SQL Converter:**

For interactive natural language queries:

```bash
uv run samples/nlp_to_sql.py
```

**Requirements:**
- Ollama running locally (`ollama serve`)
- A code-capable model (e.g., `codellama`, `deepseek-coder`)

**Learn more:** [nlp_to_sql_README.md](nlp_to_sql_README.md)

---

## Module 4: Advanced Caching Concepts

### 4.1 Performance Testing

Test cache performance under concurrent load with multi-threaded scenarios.

```bash
# Run performance test with 4 threads, 1000 queries each
uv run samples/demo_multi_threaded_performance.py --threads 4 --queries 1000

# High load test
uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000

# View results
python samples/plot_time_series.py plot-only logs/perf_test_*.json
```

**What it demonstrates:**
- Concurrency testing
- Read/write ratio analysis
- Cache hit rate under load
- Latency variance (min, avg, max)
- Time-series visualization

**Key concepts tested:**
- **Concurrency**: Multiple threads accessing cache simultaneously
- **Read/Write Ratio**: Mix of read and write operations
- **Variance**: Different sets of cacheable data
- **TTL Impact**: Time-to-live effects on hit rate

**Performance metrics:**
- Throughput: Operations per second
- Latency: Min, avg, max response times
- Cache efficiency: Hit rate percentage
- Database load: Queries per second

---

### 4.2 Use Cases for Caching

**Good candidates for caching:**
- ✅ Frequently accessed data (high read ratio)
- ✅ Expensive database queries (joins, aggregations)
- ✅ External API responses
- ✅ Session data
- ✅ Configuration data
- ✅ Computed results (analytics, reports)

**Poor candidates for caching:**
- ❌ Frequently changing data
- ❌ User-specific data with low reuse
- ❌ Data requiring strong consistency
- ❌ Large binary objects (use object storage)

---

### 4.3 Key Naming Conventions

Proper key management in a flat keyspace:

```
# Pattern: <namespace>:<entity>:<id>:<attribute>
airport:JFK:info
flight:12345:details
weather:api:newyork:current
query:hash:abc123:result

# Use separators consistently
user:session:uuid
cache:query:sql_hash
semantic:embedding:query_id
```

---

### 4.4 Eviction Policies

**LRU (Least Recently Used):**
- Evicts least recently accessed keys
- Good for: Time-sensitive data, session storage
- Use when: Access patterns favor recent data

**LFU (Least Frequently Used):**
- Evicts least frequently accessed keys
- Good for: Popular content, hot data
- Use when: Some data is consistently popular

Configure in Valkey:
```bash
# Set eviction policy
CONFIG SET maxmemory-policy allkeys-lru
# or
CONFIG SET maxmemory-policy allkeys-lfu
```

---

### 4.5 Stampede Prevention

Prevent cache stampede (thundering herd) using distributed locking.

```bash
# Run stampede prevention demo
uv run samples/demo_stampede_prevention.py --requests 1000 --threads 4 --cities 3

# High concurrency test
uv run samples/demo_stampede_prevention.py --requests 5000 --threads 10 --cities 5

# With verbose output
uv run samples/demo_stampede_prevention.py --requests 1000 --threads 4 --verbose
```

**What it demonstrates:**
- Cache stampede problem (thundering herd)
- Distributed locking with Valkey
- Exponential backoff for lock contention
- Fail-fast behavior with timeouts
- API call reduction (1000 requests → 1 API call per city)

**Key concepts:**
- **Lock TTL**: Prevents deadlocks if holder crashes
- **Exponential Backoff**: Reduces contention
- **Timeout**: Fail-fast if lock unavailable
- **Lock Key Pattern**: `lock:<resource_id>`

**Key metrics:**
- API call reduction: 90%+ for concurrent requests
- Lock wait times and retry patterns
- Stampede prevention success rate

**Learn more:** 
- [concepts/stampede_prevention.md](concepts/stampede_prevention.md)
- [implementation/stampede_prevention_demo.md](implementation/stampede_prevention_demo.md)

---

## Module 5: Other Valkey Use Cases (Optional)

### 5.1 Leaderboards for Top Airports

Demonstrate the substantial difference between analytical queries in RDBMS vs. Valkey Sorted Sets.

```bash
# Run the airport leaderboard demo
uv run samples/demo_airport_leaderboard.py --help

# With verbose output
uv run samples/demo_airport_leaderboard.py --verbose
```

**What it demonstrates:**
- Top airports by passenger count
- RDBMS analytical query: ~200ms
- Valkey Sorted Set: ~1ms (200x faster!)
- Purpose-built data structures for specific use cases

**Key concepts:**
- Sorted Sets for rankings and leaderboards
- O(log N) operations for updates
- O(1) operations for range queries
- Real-time leaderboard updates

---

### 5.2 Session Store

Demonstrate a simple application using Valkey as the session store for Flask.

```bash
# Run the session demo
FLASK_APP=session_demo/app.py uv run flask run --port 5001
```

Find a passenger passport using SQL:

```sql
SELECT * FROM passenger 
WHERE passenger_id >= (
    SELECT FLOOR(RAND() * (SELECT MAX(passenger_id) FROM passenger))
)
LIMIT 10;
```

**What it demonstrates:**
- Ephemeral session data storage
- User-specific data (zip code, flight preferences)
- Automatic session expiration
- Data cleared on logout

**Key concepts:**
- Session IDs as cache keys
- TTL for automatic cleanup
- Secure session management
- Stateless application design

---

## SQL Query Examples

The `samples/` folder includes SQL query files organized by complexity:

- **01_simple_queries.sql**: Single table operations
- **02_medium_queries.sql**: Joins and filtering (2-3 tables)
- **03_advanced_queries.sql**: Complex joins and aggregations (4+ tables)

These queries are used throughout the demos to show caching performance at different complexity levels.

---

## Documentation Index

### Caching Patterns
- [Cache-Aside Pattern](CACHE_ASIDE_README.md)
- [Write-Through Cache Pattern](WRITE_THROUGH_CACHE_README.md)
- [Stampede Prevention](concepts/stampede_prevention.md)
- [Caching Patterns Comparison](CACHING_PATTERNS_COMPARISON.md)

### Semantic Search & NLP
- [Semantic Search Demo Explained](SEMANTIC_SEARCH_DEMO_EXPLAINED.md)
- [Semantic Search Summary](SEMANTIC_SEARCH_SUMMARY.md)
- [NLP to SQL Guide](nlp_to_sql_README.md)
- [Vector vs Cache Separation](VECTOR_VS_CACHE_SEPARATION.md)

### Configuration & Migration
- [Environment Configuration](ENVIRONMENT_CONFIGURATION.md)
- [Valkey Migration Notes](VALKEY_MIGRATION_NOTES.md)
- [Valkey Naming Update](VALKEY_NAMING_UPDATE.md)

### Database
- Database schema: `flughafendb_schema_en.sql`
- Bug fixes: `bug_fixes_flughafendb_large.sql`

---

## Performance Expectations

Typical performance improvements with caching:

| Query Type | Without Cache | With Cache | Speedup |
|------------|---------------|------------|---------|
| Simple (1 table) | 5-10 ms | 0.5-1 ms | 10x |
| Medium (2-3 tables) | 15-30 ms | 1-2 ms | 15x |
| Complex (4+ tables) | 50-200 ms | 2-5 ms | 40x |
| Semantic search | 2000-5000 ms | 1-3 ms | 1000x+ |

---

## Architecture

```
┌─────────────┐
│ Application │
└──────┬──────┘
       │
       ├─────────────┐
       │             │
   ┌───▼────┐   ┌───▼─────┐
   │ Valkey │   │ MySQL/  │
   │ Cache  │   │ Postgres│
   └────────┘   └─────────┘
```

**Cache-Aside Flow:**
1. Check cache first
2. On miss, query database
3. Store result in cache
4. Return data

**Write-Through Flow:**
1. Update database
2. Update cache immediately
3. Return success

---

## Troubleshooting

### Common Issues

1. **Connection errors**: Check `.env` file for correct credentials
2. **Ollama not found**: Ensure Ollama is running (`ollama serve`)
3. **Vector index errors**: See [SEMANTIC_SEARCH_VECTOR_INDEX_FIX.md](SEMANTIC_SEARCH_VECTOR_INDEX_FIX.md)
4. **Import errors**: Run `uv sync` to install dependencies

### Getting Help

- Check the specific README files for each pattern
- Review the changelog: [CHANGELOG_ENV_MIGRATION.md](CHANGELOG_ENV_MIGRATION.md)
- Examine the sample code in `samples/` folder

---

## Workshop Summary

### Learning Path

Follow this recommended order for the best learning experience:

1. **Module 1**: Understand why caching matters (Airport App + Schema exploration)
2. **Module 2**: Learn the three core patterns (Cache-Aside → Write-Through → Write-Behind)
3. **Module 3**: Apply caching to real-world scenarios (Weather API + Semantic Cache)
4. **Module 4**: Master advanced concepts (Performance testing + Stampede prevention)
5. **Module 5**: Explore additional use cases (Leaderboards + Session Store)

### Quick Command Reference

```bash
# Run all demos automatically
python scripts/run_all_demos.py

# Run all demos with verbose output
python scripts/run_all_demos.py --verbose --interactive

# List all available demos
python scripts/run_all_demos.py --list

# Individual demos
uv run samples/demo_cache_aside.py --interactive
uv run samples/demo_write_through_cache.py --verbose
uv run samples/demo_write_behind_cache.py
uv run samples/demo_weather_api_cache.py --cities 10
uv run samples/demo_semantic_cache.py --interactive
uv run samples/demo_stampede_prevention.py --threads 10
uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000
uv run samples/demo_airport_leaderboard.py

# Visualize performance results
python samples/plot_time_series.py plot-only logs/perf_test_*.json

# Interactive tools
streamlit run airport_app.py
streamlit run session_demo/app.py
uv run samples/nlp_to_sql.py
```

### Key Takeaways

**Caching Patterns:**
- **Cache-Aside**: Best for read-heavy workloads, simple to implement
- **Write-Through**: Use when strong consistency is required
- **Write-Behind**: Maximum performance for write-heavy workloads with eventual consistency

**Performance Gains:**
- Simple queries: 10x faster
- Complex queries: 40x faster
- API calls: 500x faster
- Semantic cache: 1000x+ faster

**Critical Concepts:**
- Cache invalidation strategies
- Stampede prevention with distributed locks
- TTL optimization for different data types
- Key naming conventions for maintainability
- Eviction policies (LRU vs LFU)

**Production Considerations:**
- Monitor cache hit rates
- Set appropriate TTLs
- Implement cache warming for critical data
- Use distributed locks for high-concurrency scenarios
- Plan for cache failures (graceful degradation)

---

## Next Steps

1. **Start with Module 1**: Explore the Airport App and understand the schema
2. **Progress through Module 2**: Master the three core caching patterns
3. **Apply in Module 3**: Cache real-world APIs and AI responses
4. **Optimize in Module 4**: Test performance and prevent stampedes
5. **Extend in Module 5**: Explore leaderboards and session management

### Additional Resources

- [Workshop Guide](workshop/README.md) - Full workshop outline
- [Caching Patterns Comparison](CACHING_PATTERNS_COMPARISON.md)
- [Environment Configuration](ENVIRONMENT_CONFIGURATION.md)
- [Valkey Migration Notes](VALKEY_MIGRATION_NOTES.md)

Happy caching! 🚀
