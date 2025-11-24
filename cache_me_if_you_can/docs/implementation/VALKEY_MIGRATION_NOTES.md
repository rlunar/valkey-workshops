# Valkey Migration Notes

## Overview

This workshop uses **Valkey** as the primary caching solution. Valkey is a high-performance data structure server that is fully compatible with Redis but is open-source and community-driven.

## Import Pattern

All Python scripts in this workshop use the following import pattern to prioritize Valkey while maintaining Redis compatibility:

```python
try:
    import valkey
except ImportError:
    import redis as valkey
```

This pattern:
1. **Tries to import `valkey` first** - Uses the native Valkey client if available
2. **Falls back to `redis`** - If Valkey client is not installed, uses Redis client as `valkey`
3. **Maintains compatibility** - Works with both Valkey and Redis installations

## Why This Pattern?

### ❌ Don't Do This (Old Pattern)
```python
try:
    import valkey as redis
except ImportError:
    import redis
```

**Problems:**
- Imports Valkey but aliases it as `redis`
- Confusing naming in a Valkey workshop
- Doesn't reflect that Valkey is the primary choice

### ✅ Do This (Current Pattern)
```python
try:
    import valkey
except ImportError:
    import redis as valkey
```

**Benefits:**
- Clear that Valkey is the primary choice
- Code uses `valkey` throughout
- Falls back gracefully to Redis if needed
- Appropriate for a Valkey workshop

## Files Updated

All Python files have been updated to use the correct import pattern:

### Core Libraries
- `daos/cache_aside.py` - Cache-aside pattern implementation
- `airport_app.py` - Streamlit application

### Sample Demos
- `samples/write_through_cache_demo.py` - Write-through cache pattern
- `samples/cache_aside_demo.py` - Cache-aside pattern demo
- `samples/weather_api_cache.py` - Weather API caching demo
- `samples/semantic_search.py` - Semantic search with caching
- `samples/test_semantic_search.py` - Semantic search tests

## Environment Variables

The code supports both Redis and Valkey through the `CACHE_ENGINE` environment variable:

```bash
# Use Valkey (recommended)
CACHE_ENGINE=valkey
CACHE_HOST=localhost
CACHE_PORT=6379

# Or use Redis (fallback)
CACHE_ENGINE=redis
CACHE_HOST=localhost
CACHE_PORT=6379
```

**Note:** Both `redis` and `valkey` values work identically in the code since Valkey is protocol-compatible with Redis.

## Installation

### Install Valkey Client (Recommended)
```bash
pip install valkey
# or
uv add valkey
```

### Install Redis Client (Fallback)
```bash
pip install redis
# or
uv add redis
```

## Code Examples

### Creating a Connection
```python
try:
    import valkey
except ImportError:
    import redis as valkey

# Create client
client = valkey.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

# Use client
client.set('key', 'value')
value = client.get('key')
```

### Exception Handling
```python
try:
    client.ping()
    print("✓ Connected to Valkey")
except valkey.ConnectionError as e:
    print(f"✗ Connection failed: {e}")
```

### Response Errors
```python
try:
    client.execute_command("FT.INFO", "my_index")
except valkey.ResponseError:
    print("Index does not exist")
```

## Compatibility

Valkey is **100% compatible** with Redis at the protocol level, which means:

- ✅ All Redis commands work with Valkey
- ✅ All Redis clients work with Valkey servers
- ✅ All Valkey clients work with Redis servers
- ✅ Drop-in replacement for Redis

## Benefits of Valkey

1. **Open Source** - Truly open-source under BSD license
2. **Community-Driven** - Governed by the Linux Foundation
3. **Performance** - Same or better performance than Redis
4. **Compatibility** - 100% Redis protocol compatible
5. **No Licensing Concerns** - No SSPL or RSALv2 restrictions

## Migration from Redis

If you have existing Redis code, migration is simple:

### Before (Redis)
```python
import redis

client = redis.Redis(host='localhost', port=6379)
```

### After (Valkey)
```python
try:
    import valkey
except ImportError:
    import redis as valkey

client = valkey.Redis(host='localhost', port=6379)
```

That's it! No other code changes needed.

## Testing

All demos have been tested with both Valkey and Redis to ensure compatibility:

```bash
# Test with Valkey
uv run samples/write_through_cache_demo.py

# Test with Redis (if Valkey not installed)
uv run samples/write_through_cache_demo.py
```

## References

- [Valkey Official Website](https://valkey.io/)
- [Valkey GitHub](https://github.com/valkey-io/valkey)
- [Valkey Python Client](https://github.com/valkey-io/valkey-py)
- [Redis Compatibility](https://valkey.io/topics/compatibility/)

## Support

For issues related to:
- **Valkey installation**: See [Valkey documentation](https://valkey.io/docs/)
- **Redis fallback**: Ensure `redis` package is installed
- **Connection issues**: Check `CACHE_HOST` and `CACHE_PORT` in `.env`
- **Import errors**: Install either `valkey` or `redis` package
