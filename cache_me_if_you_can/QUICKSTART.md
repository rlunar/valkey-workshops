# Quick Start Guide

## 🚀 Run the Airport App in 3 Steps

### Step 1: Setup Environment
```bash
# Copy environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

### Step 2: Start Services
```bash
# Start database (if not running)
mysql.server start

# Start cache (if not running)
valkey-server
# or
redis-server
```

### Step 3: Run the App
```bash
# Using the convenience script (recommended)
./scripts/run_airport_app.sh

# Or directly with uv
uv run streamlit run airport_app.py
```

The app will open at **http://localhost:8501** 🎉

---

## 📋 Common Commands

### Run Airport App
```bash
uv run streamlit run airport_app.py
```

### Run Demos
```bash
# All demos
./scripts/run_all_demos.sh

# Cache-aside demo
uv run python samples/demo_cache_aside.py

# Weather API cache demo
uv run python samples/demo_weather_api_cache.py 15 10

# Write-through cache demo
uv run python samples/demo_write_through_cache.py

# Performance test
uv run python samples/demo_multi_threaded_performance.py --users 4 --queries 10
```

### NLP to SQL
```bash
# Interactive mode
uv run python daos/nlp_to_sql.py tinyllama interactive

# Demo mode
uv run python daos/nlp_to_sql.py codellama
```

---

## 🔧 Troubleshooting

### Can't connect to database?
```bash
# Check database is running
mysql -h localhost -u root -p -e "SELECT 1"

# Verify database exists
mysql -h localhost -u root -p -e "SHOW DATABASES"
```

### Can't connect to cache?
```bash
# Check cache is running
valkey-cli ping
# or
redis-cli ping

# Start cache if needed
valkey-server &
# or
redis-server &
```

### Import errors?
```bash
# Reinstall dependencies
uv sync --reinstall
```

### Port already in use?
```bash
# Change Streamlit port
uv run streamlit run airport_app.py --server.port 8502
```

---

## 📊 Using the Airport App

1. **Enter Flight ID** (try 115)
2. **Click "Get Flight Details"** - 3-table JOIN query
3. **Click again** - See cache speedup! ⚡
4. **Click "Get Manifest"** - 3-table JOIN query
5. **Select a Passenger** from the dropdown
6. **Click "Get Passenger Flights"** - 8-table JOIN query (complex!)
7. **Compare latencies** in the chart
8. **Click "Flush Cache"** to reset

### What to Observe:
- First query: ~50-300ms (database, varies by complexity)
- Second query: ~1-5ms (cache) 
- **8-table JOIN**: Most dramatic speedup!
- **Speedup: 10-200x faster!** 🚀

---

## 🎯 Quick Tips

### Best Flight IDs to Try:
- `115` - Has passengers
- `1` - First flight
- `100` - Another good example

### Environment Variables:
```bash
# Minimum required in .env
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=flughafendb_large
CACHE_HOST=localhost
CACHE_PORT=6379
```

### Performance Testing:
```bash
# Light load
uv run python samples/demo_multi_threaded_performance.py --users 2 --queries 5

# Medium load
uv run python samples/demo_multi_threaded_performance.py --users 4 --queries 10

# Heavy load
uv run python samples/demo_multi_threaded_performance.py --users 10 --queries 20
```

---

## 📚 Learn More

- **Full Documentation**: [README.md](README.md)
- **Core Modules**: [core/README.md](core/README.md)
- **Migration Guide**: [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)
- **Refactoring Details**: [docs/REFACTORING_SUMMARY.md](docs/REFACTORING_SUMMARY.md)

---

## 🆘 Need Help?

1. Check `.env` file has correct credentials
2. Verify database and cache are running
3. Check logs for error messages
4. Review documentation in `docs/` folder

**Happy Caching!** 🎉
