# Cache Me If You Can - Documentation

## Project Overview

This project demonstrates various **caching patterns** using Valkey/Redis with a realistic airport database (Flughafen). It showcases how caching can dramatically improve application performance while maintaining data consistency.

### What You'll Learn

- **Cache-Aside Pattern**: Lazy loading with automatic cache population
- **Write-Through Pattern**: Maintaining cache consistency during updates
- **Semantic Search**: Using vector embeddings for intelligent query caching
- **NLP to SQL**: Converting natural language to SQL queries with caching

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

---

## Running the Demos

All demo scripts are located in the `samples/` folder.

### 1. Cache-Aside Pattern Demo

Demonstrates lazy loading with queries of increasing complexity.

```bash
python samples/cache_aside_demo.py
```

**What it shows:**
- Simple queries (single table lookups)
- Medium queries (2-3 table joins)
- Complex queries (4+ table joins with aggregations)
- Performance comparison: cache hit vs. cache miss
- Latency improvements (typically 10-100x faster)

**Learn more:** [CACHE_ASIDE_README.md](CACHE_ASIDE_README.md)

---

### 2. Write-Through Cache Demo

Shows how to maintain cache consistency during data updates.

```bash
python samples/write_through_cache_demo.py
```

**What it shows:**
- Updating flight departure times
- Simultaneous database and cache updates
- Consistency verification
- Audit logging for all changes

**Learn more:** [WRITE_THROUGH_CACHE_README.md](WRITE_THROUGH_CACHE_README.md)

---

### 3. NLP to SQL Converter

Convert natural language questions into SQL queries using Ollama.

```bash
python samples/nlp_to_sql.py
```

**Example queries:**
- "Show me all flights from Frankfurt to New York"
- "How many passengers booked flights last month?"
- "List all airlines operating from Berlin"

**Requirements:**
- Ollama running locally (`ollama serve`)
- A code-capable model (e.g., `codellama`, `deepseek-coder`)

**Learn more:** [nlp_to_sql_README.md](nlp_to_sql_README.md)

---

### 4. Semantic Search Demo

Intelligent query caching using vector embeddings to find similar queries.

```bash
python samples/semantic_search.py
```

**What it shows:**
- Embedding-based similarity search
- Reusing cached results for similar questions
- Significant performance gains for repeated/similar queries
- Vector index management in Valkey/Redis

**Example:**
- Query: "flights from Berlin to Munich"
- Similar cached query: "show flights between Berlin and Munich"
- Result: Instant response from cache!

**Learn more:** 
- [SEMANTIC_SEARCH_DEMO_EXPLAINED.md](SEMANTIC_SEARCH_DEMO_EXPLAINED.md)
- [SEMANTIC_SEARCH_SUMMARY.md](SEMANTIC_SEARCH_SUMMARY.md)

---

### 5. Weather API Cache Demo

Real-world example of caching external API calls.

```bash
python samples/weather_api_cache.py
```

**What it shows:**
- Caching third-party API responses
- TTL-based expiration for weather data
- Reducing API costs and latency

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

## Next Steps

1. Start with the **Cache-Aside demo** to understand basic caching
2. Try the **Write-Through demo** to see consistency in action
3. Experiment with **NLP to SQL** for natural language queries
4. Explore **Semantic Search** for advanced caching strategies

Happy caching! 🚀
