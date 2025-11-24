# Environment Configuration Guide

## Overview

All Python scripts in this workshop use environment variables for configuration, managed through `.env` files. This provides flexibility and security by keeping sensitive information separate from code.

## Setup

### 1. Create Your .env File

Copy the example file and customize it:

```bash
cp .env.example .env
```

### 2. Edit Configuration

Open `.env` and update the values for your environment:

```bash
nano .env
# or
vim .env
# or use your favorite editor
```

## Configuration Reference

### Application Settings

```bash
# Use mock data for demos (true/false)
# Set to false when you have real database and cache running
USE_MOCK_DATA=false
```

### Database Configuration

```bash
# Database engine type
# Options: mysql, mariadb, postgresql
DB_ENGINE=mysql

# Database connection details
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secretpassword
DB_NAME=flughafendb_large
```

**Supported Databases:**
- MySQL 5.7+
- MariaDB 10.3+
- PostgreSQL 12+

### Cache Configuration

```bash
# Cache engine type
# Options: valkey, redis, memcached
CACHE_ENGINE=valkey

# Cache connection details
CACHE_HOST=localhost
CACHE_PORT=6379

# Cache TTL (Time To Live) in seconds
# Default: 3600 (1 hour)
CACHE_TTL=3600
```

**Supported Cache Engines:**
- Valkey (recommended)
- Redis
- Memcached

### Ollama Configuration

```bash
# Model to use for NLP to SQL conversion
# Options: codellama, tinyllama, llama2, mistral, etc.
OLLAMA_MODEL=codellama

# Ollama API endpoint
OLLAMA_URL=http://localhost:11434/api/generate
```

**Recommended Models:**
- `codellama` - Best for SQL generation (recommended)
- `tinyllama` - Faster, less accurate
- `llama2` - Good balance
- `mistral` - High quality, slower

### Embedding Model Configuration

```bash
# Model for semantic search embeddings
# Options: all-MiniLM-L6-v2, all-mpnet-base-v2, etc.
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

**Available Models:**
- `all-MiniLM-L6-v2` - Fast, good quality (recommended)
- `all-mpnet-base-v2` - Higher quality, slower
- `paraphrase-multilingual-MiniLM-L12-v2` - Multilingual support

### Semantic Search Configuration

```bash
# Similarity threshold for semantic search (0.0 to 1.0)
# Higher = more strict matching
SIMILARITY_THRESHOLD=0.70
```

**Threshold Guidelines:**
- `0.90-1.0` - Very strict (exact matches only)
- `0.70-0.89` - Moderate (recommended)
- `0.50-0.69` - Loose (more results)
- `<0.50` - Very loose (may include irrelevant results)

### Knowledge Base Configuration

```bash
# Path to knowledge base directory
# Relative to the script location
KNOWLEDGE_BASE_PATH=../knowledge_base
```

### Vector Database Configuration

```bash
# Vector database for semantic search (can be same as cache or different)
# Options: valkey, redis
VECTOR_ENGINE=valkey
VECTOR_HOST=localhost
VECTOR_PORT=16379
```

**Why Separate Vector Database?**
- Vector search requires RediSearch/Valkey Search module
- Allows independent scaling of vector operations
- Can use different instance from regular cache
- Isolates vector workloads from cache workloads

**Same vs Different Instance:**
- **Same instance** (VECTOR_PORT=6379): Simpler setup, shared resources
- **Different instance** (VECTOR_PORT=16379): Better isolation, independent scaling

## Usage in Python Scripts

All scripts automatically load environment variables using `python-dotenv`:

```python
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Access configuration
db_host = os.getenv("DB_HOST", "localhost")
cache_port = int(os.getenv("CACHE_PORT", "6379"))
model = os.getenv("OLLAMA_MODEL", "codellama")
```

## Scripts Using Environment Variables

### Core Libraries
- `daos/cache_aside.py` - Database and cache configuration
- `airport_app.py` - All configuration options

### Demos
- `samples/write_through_cache_demo.py` - Database and cache
- `samples/cache_aside_demo.py` - Database and cache
- `samples/weather_api_cache.py` - Cache configuration
- `samples/nlp_to_sql.py` - Ollama and knowledge base
- `samples/semantic_search.py` - All configuration options
- `samples/test_semantic_search.py` - Embedding model

## Environment-Specific Configurations

### Development Environment

```bash
USE_MOCK_DATA=false
DB_HOST=localhost
CACHE_HOST=localhost
OLLAMA_MODEL=tinyllama  # Faster for development
CACHE_TTL=300  # 5 minutes for faster testing
```

### Production Environment

```bash
USE_MOCK_DATA=false
DB_HOST=production-db.example.com
DB_PORT=3306
CACHE_HOST=production-cache.example.com
CACHE_PORT=6379
OLLAMA_MODEL=codellama  # Best quality
CACHE_TTL=3600  # 1 hour
```

### Demo/Presentation Environment

```bash
USE_MOCK_DATA=true  # No real DB/cache needed
OLLAMA_MODEL=tinyllama  # Fast responses
```

## Security Best Practices

### 1. Never Commit .env Files

The `.env` file is in `.gitignore` to prevent accidental commits:

```bash
# Check if .env is ignored
git check-ignore .env
# Should output: .env
```

### 2. Use Strong Passwords

```bash
# Bad
DB_PASSWORD=password

# Good
DB_PASSWORD=xK9$mP2#vL8@nQ5!
```

### 3. Restrict File Permissions

```bash
# Make .env readable only by owner
chmod 600 .env
```

### 4. Use Different Credentials Per Environment

Don't use the same passwords for development, staging, and production.

## Troubleshooting

### Issue: Environment Variables Not Loading

**Solution 1:** Check file location
```bash
# .env should be in project root
ls -la .env
```

**Solution 2:** Check file format
```bash
# No spaces around =
# Bad:  DB_HOST = localhost
# Good: DB_HOST=localhost
```

**Solution 3:** Restart application
```bash
# Environment variables are loaded at startup
# Restart after changing .env
```

### Issue: Connection Errors

**Check database connection:**
```bash
# Test MySQL connection
mysql -h localhost -u root -p -e "SELECT 1"

# Test PostgreSQL connection
psql -h localhost -U postgres -c "SELECT 1"
```

**Check cache connection:**
```bash
# Test Valkey/Redis connection
valkey-cli ping
# or
redis-cli ping

# Test Memcached connection
echo "stats" | nc localhost 11211
```

**Check Ollama:**
```bash
# Test Ollama API
curl http://localhost:11434/api/tags
```

### Issue: Model Not Found

**Solution:** Pull the model first
```bash
# Pull Ollama model
ollama pull codellama

# List available models
ollama list
```

### Issue: Import Error for dotenv

**Solution:** Install python-dotenv
```bash
# Using pip
pip install python-dotenv

# Using uv
uv add python-dotenv
```

## Environment Variable Precedence

Variables are loaded in this order (later overrides earlier):

1. System environment variables
2. `.env` file in project root
3. Default values in code

Example:
```bash
# In .env
DB_HOST=localhost

# In terminal
export DB_HOST=production-db.example.com

# Python will use: production-db.example.com
```

## Testing Configuration

### Verify Environment Loading

```python
from dotenv import load_dotenv
import os

load_dotenv()

print("Database:", os.getenv("DB_HOST"))
print("Cache:", os.getenv("CACHE_HOST"))
print("Model:", os.getenv("OLLAMA_MODEL"))
```

### Test Database Connection

```bash
uv run python -c "from daos.cache_aside import CacheAside; c = CacheAside(); print('✓ Connected')"
```

### Test Cache Connection

```bash
uv run python -c "import os; from dotenv import load_dotenv; load_dotenv(); import valkey; c = valkey.Redis(host=os.getenv('CACHE_HOST'), port=int(os.getenv('CACHE_PORT'))); c.ping(); print('✓ Cache connected')"
```

## Docker Compose Integration

If using Docker Compose, you can reference the `.env` file:

```yaml
# docker-compose.yml
services:
  app:
    env_file:
      - .env
    environment:
      - DB_HOST=mysql
      - CACHE_HOST=valkey
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
env:
  DB_HOST: localhost
  DB_USER: root
  DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  CACHE_HOST: localhost
  OLLAMA_MODEL: tinyllama
```

### GitLab CI

```yaml
# .gitlab-ci.yml
variables:
  DB_HOST: "localhost"
  CACHE_HOST: "localhost"
  OLLAMA_MODEL: "tinyllama"
```

## References

- [python-dotenv Documentation](https://github.com/theskumar/python-dotenv)
- [12-Factor App: Config](https://12factor.net/config)
- [Environment Variables Best Practices](https://12factor.net/config)

## Support

For configuration issues:
1. Check this documentation
2. Verify `.env` file exists and has correct format
3. Test connections individually
4. Check application logs for specific errors
