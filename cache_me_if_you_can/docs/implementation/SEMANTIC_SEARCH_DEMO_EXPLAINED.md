# Semantic Search Demo - Detailed Explanation

## Overview

The semantic search demo now provides detailed information about cache hits/misses, showing exactly why each query resulted in a cache hit or miss, which keys are used, and how similar queries are to each other.

## Running the Demo

### Basic Demo
```bash
uv run python samples/semantic_search.py --mode demo
```

### Verbose Demo (Shows Embeddings and Keys)
```bash
uv run python samples/semantic_search.py --mode demo --verbose
```

## Demo Output Explained

### Query #1: First Query (Cache Miss)

```
======================================================================
Query #1: Flight manifest - all passengers on a specific flight 115
======================================================================

🔑 Key Information: (--verbose only)
   Prompt hash: a3f5b2c8d1e4f6a7...
   Semantic key: semantic:prompt:a3f5b2c8d1e4f6a7...
   Embedding key: embedding:prompt:a3f5b2c8d1e4f6a7...

──────────────────────────────────────────────────────────────────────
🤖 CACHE MISS - New Query
──────────────────────────────────────────────────────────────────────
   Reason: No similar queries found in cache
   Similarity threshold: 0.70
   Action: Generating SQL with LLM (codellama model)

   ⏱️  Generation Stats:
      Time taken: 3.45s
      Tokens used: 1234
      Prompt tokens: 890
      Response tokens: 344

   💾 Caching for future: (--verbose only)
      Storing embedding vector (384 dimensions)
      Creating semantic mapping
      Enabling similarity search for future queries

📄 Generated SQL:
──────────────────────────────────────────────────────────────────────
SELECT p.firstname, p.lastname, b.seat
FROM booking b
JOIN passenger p ON b.passenger_id = p.passenger_id
WHERE b.flight_id = 115;
```

**Explanation:**
- **Cache Miss**: This is the first time we've seen this query
- **No Similar Queries**: The cache is empty, so no similar queries exist
- **LLM Generation**: The query is sent to Ollama (codellama model)
- **Caching**: The result is stored with its embedding for future similarity searches

### Query #2: Similar Query (Semantic Cache Hit)

```
======================================================================
Query #2: Give me the passenger details from flight 115
======================================================================

──────────────────────────────────────────────────────────────────────
✨ SEMANTIC CACHE HIT
──────────────────────────────────────────────────────────────────────
   Reason: Found similar query in cache
   Similarity score: 0.8542 (threshold: 0.70)
   Match quality: Good

   📊 Embedding Details: (--verbose only)
      Current embedding: [0.123, -0.456, 0.789, 0.234, -0.567...]
      Similar embedding: [0.145, -0.432, 0.801, 0.221, -0.589...]
      Vector dimension: 384
      Cosine similarity: 0.8542

   📝 Matched Query:
      Original: "Flight manifest - all passengers on a specific flight 115"
      Current:  "Give me the passenger details from flight 115"

   ⚡ Performance:
      Lookup time: 0.012s
      Saved ~3.5s of LLM generation

📄 Generated SQL:
──────────────────────────────────────────────────────────────────────
SELECT p.firstname, p.lastname, b.seat
FROM booking b
JOIN passenger p ON b.passenger_id = p.passenger_id
WHERE b.flight_id = 115;
```

**Explanation:**
- **Semantic Cache Hit**: Found a similar query in the cache
- **Similarity Score**: 0.8542 (above threshold of 0.70)
- **Match Quality**: "Good" (0.8-0.9 range)
- **Performance**: Retrieved in 0.012s vs 3.5s for LLM generation
- **Same SQL**: Returns the same SQL as the original query

### Query #7: Exact Repeat (Exact Cache Hit)

```
======================================================================
Query #7: How many bookings does passenger 1000 have?
======================================================================

──────────────────────────────────────────────────────────────────────
🎯 EXACT CACHE HIT
──────────────────────────────────────────────────────────────────────
   Reason: Exact same query seen before
   Match type: Hash-based exact match
   Lookup time: 0.001s (instant)

   🔑 Cache Keys: (--verbose only)
      Semantic key: semantic:prompt:b7d9e2f1a4c6...
      Query key: db:query:c3a5f8d2b1e4...

📄 Generated SQL:
──────────────────────────────────────────────────────────────────────
SELECT COUNT(*) FROM booking WHERE passenger_id = 1000;
```

**Explanation:**
- **Exact Cache Hit**: The exact same query was seen before (Query #6)
- **Hash-based**: Uses SHA1 hash for instant lookup
- **Instant**: Retrieved in 0.001s (no embedding comparison needed)
- **Most Efficient**: Fastest possible cache retrieval

## Cache Hit Types

### 1. Exact Cache Hit (🎯)

**When it happens:**
- Exact same query text seen before
- Hash matches exactly

**How it works:**
```
Query → SHA1 Hash → semantic:prompt:{hash} → db:query:{hash} → Result
```

**Performance:**
- Lookup time: ~0.001s (instant)
- No embedding comparison needed
- Most efficient

**Example:**
```
Query 1: "How many bookings does passenger 1000 have?"
Query 2: "How many bookings does passenger 1000 have?"  ← Exact match
```

### 2. Semantic Cache Hit (✨)

**When it happens:**
- Similar query found in cache
- Cosine similarity >= threshold (default 0.70)

**How it works:**
```
Query → Generate Embedding → Vector Search → Find Similar → Check Threshold → Return Result
```

**Performance:**
- Lookup time: ~0.010-0.050s
- Requires embedding generation and similarity calculation
- Still much faster than LLM generation

**Example:**
```
Query 1: "Flight manifest - all passengers on a specific flight 115"
Query 2: "Give me the passenger details from flight 115"  ← Similar (0.85)
```

### 3. Cache Miss (🤖)

**When it happens:**
- No similar queries in cache
- All similarities below threshold

**How it works:**
```
Query → Search Cache → No Match → Generate with LLM → Cache Result
```

**Performance:**
- Generation time: ~2-5s (depends on model and query complexity)
- Stores result for future queries

## Similarity Scores Explained

### Score Ranges

| Score | Quality | Description |
|-------|---------|-------------|
| 0.95-1.00 | Excellent | Nearly identical queries |
| 0.85-0.94 | Very Good | Very similar meaning |
| 0.70-0.84 | Good | Similar enough to reuse |
| 0.50-0.69 | Fair | Some similarity (below threshold) |
| 0.00-0.49 | Poor | Different queries |

### Example Similarities

```
Query A: "Show all passengers on flight 115"
Query B: "Give me passenger list for flight 115"
Similarity: 0.92 (Excellent) ✅

Query A: "Show all passengers on flight 115"
Query C: "What is the weather in New York?"
Similarity: 0.15 (Poor) ❌
```

## Key Structure

### Semantic Key
```
semantic:prompt:{sha1_hash}
```
- Maps prompt hash to query result key
- Used for exact matching
- Example: `semantic:prompt:a3f5b2c8d1e4f6a7...`

### Query Key
```
db:query:{sha1_hash}
```
- Stores the actual SQL result
- Contains: sql, time_taken, tokens, model, etc.
- Example: `db:query:c3a5f8d2b1e4...`

### Embedding Key
```
embedding:prompt:{sha1_hash}
```
- Stores the embedding vector
- Used for vector similarity search
- Contains: prompt text, query_key, embedding bytes
- Example: `embedding:prompt:a3f5b2c8d1e4f6a7...`

## Embedding Details (--verbose)

When running with `--verbose`, you'll see embedding information:

```
📊 Embedding Details:
   Current embedding: [0.123, -0.456, 0.789, 0.234, -0.567...]
   Similar embedding: [0.145, -0.432, 0.801, 0.221, -0.589...]
   Vector dimension: 384
   Cosine similarity: 0.8542
```

**What this shows:**
- **Current embedding**: Vector representation of current query
- **Similar embedding**: Vector representation of matched query
- **Vector dimension**: Size of embedding (384 for all-MiniLM-L6-v2)
- **Cosine similarity**: How similar the vectors are (0-1 scale)

## Demo Summary

At the end of the demo, you'll see:

```
======================================================================
📈 DEMO SUMMARY
======================================================================
   Total queries: 7
   Cache hits: 5 (71.4%)
   Cache misses: 2
   Total LLM time: 6.89s
   Average per new query: 3.45s

📊 CACHE STATISTICS
======================================================================
   Cached prompts: 4
   Cached queries: 4
   Embeddings stored: 4
   Cache efficiency: 71.4%
   Time saved: ~17.3s
======================================================================
```

**Metrics explained:**
- **Cache hits**: Queries served from cache (exact + semantic)
- **Cache misses**: Queries that required LLM generation
- **Cache efficiency**: Percentage of queries served from cache
- **Time saved**: Total time saved by not regenerating SQL

## Performance Comparison

| Operation | Time | Speedup |
|-----------|------|---------|
| LLM Generation | ~3.5s | 1x (baseline) |
| Semantic Cache Hit | ~0.015s | 233x faster |
| Exact Cache Hit | ~0.001s | 3500x faster |

## Use Cases

### 1. User Variations
Different users asking the same thing in different ways:
- "Show me flights from JFK"
- "List all flights departing from JFK"
- "What flights leave from JFK?"

All hit semantic cache! ✨

### 2. Typos and Variations
Minor differences don't matter:
- "passenger details for flight 115"
- "passenger detail for flight 115" (singular)

Still matches! ✨

### 3. Exact Repeats
Same user asking the same question:
- First time: Cache miss (3.5s)
- Second time: Exact hit (0.001s)

3500x faster! 🎯

## Troubleshooting

### Low Similarity Scores

If queries that should match have low similarity:
1. Check similarity threshold (default 0.70)
2. Try lowering threshold: `--threshold 0.60`
3. Verify embedding model is loaded correctly

### No Semantic Hits

If only getting exact hits or misses:
1. Check if vector search is working
2. Verify RediSearch module is loaded
3. Check index creation in verbose mode

### Slow Lookups

If cache lookups are slow:
1. Check vector database connection
2. Verify index exists
3. Monitor vector database performance

## Advanced Usage

### Custom Threshold
```bash
# More strict (only very similar queries)
uv run python samples/semantic_search.py --threshold 0.85

# More lenient (more cache hits)
uv run python samples/semantic_search.py --threshold 0.60
```

### Clear Cache
```bash
# Start fresh
uv run python samples/semantic_search.py --clear
```

### Interactive Mode
```bash
# Try your own queries
uv run python samples/semantic_search.py --mode interactive --verbose
```

## References

- [Cosine Similarity](https://en.wikipedia.org/wiki/Cosine_similarity)
- [Sentence Transformers](https://www.sbert.net/)
- [Vector Search](https://redis.io/docs/stack/search/reference/vectors/)

---

**Document Date:** November 20, 2025  
**Status:** ✅ Complete
