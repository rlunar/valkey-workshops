# Quick Start Guide - NLP to SQL with Semantic Caching

## 🚀 Get Started in 3 Steps

### 1. Install Dependencies
```bash
uv sync
```

### 2. Start Required Services
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Redis/Valkey
redis-server
# or
valkey-server

# Terminal 3: Pull a good model (optional but recommended)
ollama pull llama3.2
```

### 3. Run the Demo
```bash
# Test components first
uv run python samples/test_semantic_search.py

# Run semantic search demo
uv run python samples/semantic_search.py --model llama3.2
```

## 📁 What's Included

### Core Files

| File | Purpose |
|------|---------|
| `nlp_to_sql.py` | Basic NLP to SQL converter using Ollama |
| `semantic_search.py` | Smart caching with vector similarity |
| `test_semantic_search.py` | Test embedding and similarity |

### Documentation

| File | Content |
|------|---------|
| `nlp_to_sql_README.md` | NLP to SQL documentation |
| `semantic_search_README.md` | Semantic cache documentation |
| `SEMANTIC_SEARCH_SUMMARY.md` | Architecture and results |
| `QUICK_START.md` | This file |

### Knowledge Base

| Directory | Content |
|-----------|---------|
| `knowledge_base/` | Database schema JSON files |
| `knowledge_base/*.json` | Table definitions, examples, guides |

## 🎯 Common Use Cases

### 1. Basic SQL Generation
```bash
# Simple NLP to SQL (no caching)
uv run python samples/nlp_to_sql.py llama3.2
```

### 2. Interactive SQL Generation
```bash
# Interactive mode
uv run python samples/nlp_to_sql.py llama3.2 interactive
```

### 3. Semantic Caching (Recommended)
```bash
# Demo mode - shows caching in action
uv run python samples/semantic_search.py --model llama3.2

# Interactive with caching
uv run python samples/semantic_search.py --model llama3.2 --mode interactive
```

### 4. Custom Threshold
```bash
# Stricter matching (0.80)
uv run python samples/semantic_search.py --model llama3.2 --threshold 0.80

# Looser matching (0.60)
uv run python samples/semantic_search.py --model llama3.2 --threshold 0.60
```

## 🔧 Troubleshooting

### "Module not found: sentence_transformers"
```bash
uv sync
```

### "Cannot connect to Ollama"
```bash
# Start Ollama
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

### "Cannot connect to Redis"
```bash
# Start Redis
redis-server

# Or Valkey
valkey-server

# Check if running
redis-cli ping
```

### "First run is slow"
- Embedding model downloads on first use (~90MB)
- Ollama model downloads on first use (varies by model)
- Subsequent runs are fast

### "Poor cache hit rate"
```bash
# Lower the threshold
uv run python samples/semantic_search.py --threshold 0.60
```

## 📊 Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| First run (model download) | 1-2 min | One-time only |
| Embedding generation | ~10ms | Per query |
| Vector search | <1ms | Per query |
| LLM generation (TinyLlama) | 2-3s | Cache miss |
| LLM generation (Llama3.2) | 3-5s | Cache miss |
| Cache hit | ~20ms | 175x faster! |

## 🎓 Learning Path

1. **Start here**: Run `test_semantic_search.py` to understand embeddings
2. **Basic usage**: Try `nlp_to_sql.py` to see SQL generation
3. **Advanced**: Use `semantic_search.py` to see caching in action
4. **Customize**: Adjust thresholds and models for your use case

## 💡 Tips

1. **Use better models**: `llama3.2` or `mistral` instead of `tinyllama`
2. **Adjust threshold**: Start with 0.70, tune based on your queries
3. **Monitor cache**: Use `stats` command in interactive mode
4. **Clear cache**: Use `--clear` flag to start fresh

## 🔗 Related Files

- Database schema: `knowledge_base/*.json`
- SQL examples: `samples/*.sql`
- Cache implementation: `daos/cache_aside.py`

## 📚 Next Steps

1. Read `SEMANTIC_SEARCH_SUMMARY.md` for architecture details
2. Check `semantic_search_README.md` for advanced usage
3. Explore `knowledge_base/` to understand the database schema
4. Try different Ollama models for better SQL quality

## 🆘 Need Help?

1. Check the README files in `samples/`
2. Run test scripts to verify components
3. Review example queries in `knowledge_base/nl_sql_examples.json`
4. Check Ollama logs: `ollama logs`

---

**Ready to go?** Start with:
```bash
uv run python samples/test_semantic_search.py
```
