# 3.2 GenAI Semantic Caching

## Overview

Explore semantic caching for GenAI applications using Valkey Vector Similarity Search to reduce model calls and token usage.

## Objectives

- Implement semantic caching for NLP to SQL conversion
- Use Valkey Vector Similarity Search
- Bundle similar prompts to reduce model calls
- Reduce latency and token consumption

## Use Case

Converting natural language prompts to SQL queries using GenAI:
- Similar prompts can reuse cached results
- Vector similarity identifies semantically similar queries
- Reduces expensive model API calls

## Hands-on Demo

[Demo content showing NLP to SQL with semantic caching]

Let's see the options available in the script:

```bash
uv run samples/demo_semantic_cache.py --help
```

Expected Output

```bash
 Usage: demo_semantic_cache.py [OPTIONS]

 Run the semantic cache pattern demonstration

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --interactive         -i               Run in interactive mode for custom queries                                                                                                │
│ --verbose             -v               Show detailed information including embeddings and cache keys                                                                             │
│ --flush               -f               Flush cache before running demo                                                                                                           │
│ --host                        TEXT     Valkey host (default: from VECTOR_HOST env or localhost)                                                                                  │
│ --port                        INTEGER  Valkey port (default: from VECTOR_PORT env or 6379)                                                                                       │
│ --model                       TEXT     Ollama model for SQL generation (default: from OLLAMA_MODEL env or codellama)                                                             │
│ --threshold                   FLOAT    Similarity threshold 0-1 (default: from SIMILARITY_THRESHOLD env or 0.70)                                                                 │
│ --install-completion                   Install completion for the current shell.                                                                                                 │
│ --show-completion                      Show completion for the current shell, to copy it or customize the installation.                                                          │
│ --help                                 Show this message and exit.                                                                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Run the demo with verbose output:

```bash
uv run samples/demo_semantic_cache.py -f -v
```

## Performance Metrics

- Reduction in model API calls
- Token usage savings
- Latency improvements

## Key Takeaways

- Semantic similarity enables intelligent caching
- Vector search is powerful for AI applications
- Significant cost savings with high cache hit rates
