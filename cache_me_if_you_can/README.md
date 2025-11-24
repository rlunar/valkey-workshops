# Cache Me If You Can - Valkey Workshop

A comprehensive workshop demonstrating caching patterns with Valkey/Redis and relational databases.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- MySQL/MariaDB database
- Valkey or Redis cache server

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd cache_me_if_you_can

# Install dependencies
uv sync
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required configuration:
```bash
# Database
DB_ENGINE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=flughafendb_large

# Cache
CACHE_ENGINE=valkey
CACHE_HOST=localhost
CACHE_PORT=6379
```

### Database Setup

```bash
# Import the database
gunzip -c data/flughafendb_large_20251120_113432.sql.gz | mysql -u root -p
```

## Running the Applications

### Airport App (Streamlit)

Interactive web application demonstrating cache-aside pattern:

```bash
# Using the convenience script
./scripts/run_airport_app.sh

# Or directly with uv
uv run streamlit run airport_app.py
```

The app will open at http://localhost:8501

**Features:**
- Flight details query (3-table JOIN)
- Flight manifest query (3-table JOIN)
- Passenger flights query (8-table JOIN - complex!)
- Real-time performance metrics
- Cache vs database latency comparison
- Cache hit rate statistics
- Random passenger selection
- Multi-database support (MySQL, MariaDB, PostgreSQL)

### Demo Scripts

Run all demos:
```bash
./scripts/run_all_demos.sh
```

Or run individual demos:

```bash
# Cache-aside pattern demo
uv run python samples/demo_cache_aside.py

# Weather API cache demo
uv run python samples/demo_weather_api_cache.py

# Write-through cache demo
uv run python samples/demo_write_through_cache.py

# Stampede prevention demo (distributed locking)
uv run python samples/demo_stampede_prevention.py --threads 10 --cities 3

# Multi-threaded performance test
uv run python samples/demo_multi_threaded_performance.py --users 4 --queries 10
```

### NLP to SQL

Natural language to SQL query generation:

```bash
# Interactive mode
uv run python daos/nlp_to_sql.py tinyllama interactive

# Demo mode
uv run python daos/nlp_to_sql.py codellama
```

## Project Structure

```
cache_me_if_you_can/
├── core/                      # Centralized connection modules
│   ├── rdbms.py              # Database connection manager
│   ├── inmemory.py           # Cache connection manager
│   └── README.md             # Core module documentation
├── daos/                      # Data access objects
│   ├── cache_aside.py        # Cache-aside pattern implementation
│   └── nlp_to_sql.py         # NLP to SQL converter
├── samples/                   # Demo applications
│   ├── demo_cache_aside.py
│   ├── demo_weather_api_cache.py
│   ├── demo_write_through_cache.py
│   ├── demo_stampede_prevention.py
│   └── demo_multi_threaded_performance.py
├── services/                  # Service layer
│   └── weather_service.py    # Mock weather service
├── knowledge_base/            # NLP to SQL knowledge base
├── docs/                      # Documentation
│   ├── REFACTORING_SUMMARY.md
│   ├── MIGRATION_GUIDE.md
│   └── AIRPORT_APP_REFACTORING.md
├── scripts/                   # Utility scripts
│   ├── run_airport_app.sh
│   └── run_all_demos.sh
├── airport_app.py            # Streamlit web application
└── pyproject.toml            # Project dependencies
```

## Caching Patterns Demonstrated

### 1. Cache-Aside (Lazy Loading)
- Read from cache first
- On miss, read from database
- Store in cache for future requests
- **Demo:** `samples/demo_cache_aside.py`

### 2. Write-Through Cache
- Write to database first
- Immediately update cache
- Ensures consistency
- **Demo:** `samples/demo_write_through_cache.py`

### 3. Cache with External API
- Cache expensive API calls
- Distributed locking to prevent stampede
- TTL-based expiration
- **Demo:** `samples/demo_weather_api_cache.py`

## Core Modules

The project uses centralized connection management:

### Database Connections (`core/rdbms.py`)
```python
from core import get_db_engine

engine = get_db_engine()
with engine.connect() as conn:
    result = conn.execute(query)
```

### Cache Connections (`core/inmemory.py`)
```python
from core import get_cache_client

cache = get_cache_client()
cache.set("key", "value", ttl=3600)
value = cache.get("key")
```

See `core/README.md` for detailed documentation.

## Documentation

- **[Core Module Documentation](core/README.md)** - Connection management
- **[Refactoring Summary](docs/REFACTORING_SUMMARY.md)** - Code refactoring details
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - How to use core modules
- **[Airport App Refactoring](docs/AIRPORT_APP_REFACTORING.md)** - Streamlit app changes

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_ENGINE` | Database type (mysql, mariadb, postgresql) | mysql |
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 3306 |
| `DB_USER` | Database user | root |
| `DB_PASSWORD` | Database password | |
| `DB_NAME` | Database name | flughafendb_large |
| `CACHE_ENGINE` | Cache type (redis, valkey, memcached) | valkey |
| `CACHE_HOST` | Cache host | localhost |
| `CACHE_PORT` | Cache port | 6379 |
| `CACHE_TTL` | Default TTL in seconds | 3600 |
| `OLLAMA_MODEL` | Model for NLP to SQL | codellama |
| `OLLAMA_URL` | Ollama API URL | http://localhost:11434/api/generate |

## Troubleshooting

### Database Connection Issues
```bash
# Test database connection
mysql -h localhost -u root -p -e "SELECT 1"

# Check database exists
mysql -h localhost -u root -p -e "SHOW DATABASES LIKE 'flughafendb%'"
```

### Cache Connection Issues
```bash
# Test Valkey connection
valkey-cli ping

# Or Redis
redis-cli ping

# Check if cache is running
ps aux | grep valkey
```

### Import Errors
```bash
# Reinstall dependencies
uv sync --reinstall

# Or install specific package
uv pip install streamlit
```

## Performance Tips

1. **Database Indexes**: Ensure proper indexes on frequently queried columns
2. **Cache TTL**: Adjust TTL based on data volatility
3. **Connection Pooling**: Configure pool size based on concurrent users
4. **Query Optimization**: Use EXPLAIN to analyze slow queries

## Contributing

See individual module READMEs for development guidelines:
- `core/README.md` - Core module development
- `docs/MIGRATION_GUIDE.md` - Code migration patterns

## License

[Add your license here]

## Resources

- [Valkey Documentation](https://valkey.io/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Streamlit Documentation](https://docs.streamlit.io/)
