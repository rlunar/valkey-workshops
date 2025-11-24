# Scripts Overview

## Available Scripts

The project includes two versions of the run_all_demos script:

### 1. Shell Script (Bash)
**File:** `scripts/run_all_demos.sh`

**Best for:**
- Unix/Linux/macOS systems
- CI/CD pipelines
- Users familiar with bash
- Minimal dependencies

**Usage:**
```bash
./scripts/run_all_demos.sh
./scripts/run_all_demos.sh --help
```

**Features:**
- ✅ No Python dependencies
- ✅ Fast execution
- ✅ Color-coded output
- ✅ Box drawing characters
- ✅ Interactive prompts
- ❌ Unix-only (no Windows)

---

### 2. Python Script (Typer + Rich)
**File:** `scripts/run_all_demos.py`

**Best for:**
- Cross-platform compatibility
- Windows users
- Rich terminal formatting
- Extensibility and customization

**Usage:**
```bash
python scripts/run_all_demos.py
python scripts/run_all_demos.py --help
python scripts/run_all_demos.py --skip-prompts
```

**Features:**
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Beautiful Rich formatting
- ✅ Progress indicators
- ✅ Detailed error handling
- ✅ Type-safe with Typer
- ✅ Easy to extend
- ⚠️ Requires Python + packages

---

## Quick Comparison

| Feature | Shell Script | Python Script |
|---------|-------------|---------------|
| **Platform** | Unix/Linux/macOS | All platforms |
| **Dependencies** | bash, uv | Python, typer, rich |
| **Formatting** | Basic colors | Rich formatting |
| **Progress** | None | Spinners |
| **Error Handling** | Basic | Comprehensive |
| **Extensibility** | Moderate | Easy |
| **Speed** | Fast | Slightly slower |
| **Interactive** | Yes | Yes |

---

## Which One to Use?

### Use Shell Script if:
- You're on Unix/Linux/macOS
- You want minimal dependencies
- You need fast execution
- You're running in CI/CD

### Use Python Script if:
- You're on Windows
- You want beautiful output
- You need detailed error messages
- You plan to extend functionality

---

## Common Usage Patterns

### Run All Demos (Interactive)
```bash
# Shell
./scripts/run_all_demos.sh

# Python
python scripts/run_all_demos.py
```

### Run All Demos (Non-Interactive)
```bash
# Shell
# (Not directly supported, but you can pipe 'yes')
yes | ./scripts/run_all_demos.sh

# Python
python scripts/run_all_demos.py --skip-prompts
```

### Show Help
```bash
# Shell
./scripts/run_all_demos.sh --help

# Python
python scripts/run_all_demos.py --help
```

---

## Individual Demo Scripts

Both scripts run these demos in order:

1. **Cache-Aside Pattern** (`demo_cache_aside.py`)
   - Read-through caching with lazy loading
   - Rich tables and verbose mode

2. **Write-Through Cache** (`demo_write_through_cache.py`)
   - Synchronous writes to DB and cache
   - Consistency verification

3. **Write-Behind Cache** (`demo_write_behind_cache.py`)
   - Asynchronous writes with queue
   - Batch processing

4. **Weather API Cache** (`demo_weather_api_cache.py`)
   - Real-world API caching
   - Country flags 🇺🇸 🇲🇽 🇬🇧
   - Weather emojis ☀️ 🌧️ ⛅
   - Syntax-highlighted JSON

5. **Semantic Search** (`demo_semantic_search.py`)
   - Vector similarity search
   - Embeddings required

6. **Multi-threaded Performance** (`demo_multi_threaded_performance.py`)
   - Concurrent load testing
   - Performance metrics
   - JSON output

---

## Running Individual Demos

You can also run demos individually with custom options:

### Cache-Aside
```bash
uv run samples/demo_cache_aside.py --interactive --verbose
```

### Write-Through
```bash
uv run samples/demo_write_through_cache.py --interactive
```

### Weather API
```bash
# Basic
uv run samples/demo_weather_api_cache.py

# With options
uv run samples/demo_weather_api_cache.py --verbose --cities 5 --ttl 30

# Interactive with flush
uv run samples/demo_weather_api_cache.py -i -v -f
```

### Multi-threaded Performance
```bash
# Default (4 users, 10 queries)
uv run samples/demo_multi_threaded_performance.py

# Custom load
uv run samples/demo_multi_threaded_performance.py --users 8 --queries 20

# With output file
uv run samples/demo_multi_threaded_performance.py --output my_test.json
```

---

## Tips and Tricks

### 1. Skip Specific Demos
Edit the script and comment out demos you don't want to run.

### 2. Customize Demo Arguments
Modify the `args` parameter in the script:

**Shell:**
```bash
run_demo "Weather API Cache Demo" "demo_weather_api_cache.py" "--cities 10 --ttl 60"
```

**Python:**
```python
runner.run_demo(
    name="Weather API Cache Demo",
    script="demo_weather_api_cache.py",
    args=["--cities", "10", "--ttl", "60"]
)
```

### 3. Save Output to File
```bash
# Shell
./scripts/run_all_demos.sh > demo_output.log 2>&1

# Python
python scripts/run_all_demos.py > demo_output.log 2>&1
```

### 4. Run in Background
```bash
# Shell
nohup ./scripts/run_all_demos.sh &

# Python
nohup python scripts/run_all_demos.py --skip-prompts &
```

---

## Troubleshooting

### Script Not Executable
```bash
chmod +x scripts/run_all_demos.sh
chmod +x scripts/run_all_demos.py
```

### Missing Dependencies (Python)
```bash
uv sync
# or
pip install typer rich
```

### Valkey/Redis Not Running
```bash
# Check if running
redis-cli ping

# Start Valkey/Redis
# (depends on your installation method)
```

### .env File Missing
```bash
cp .env.example .env
# Edit .env with your configuration
```

---

## Documentation

- **Shell Script**: See `docs/RUN_ALL_DEMOS_UPDATES.md`
- **Python Script**: See `docs/RUN_ALL_DEMOS_PYTHON.md`
- **Weather Demo**: See `docs/WEATHER_DEMO_FINAL_SUMMARY.md`
- **Verbose Mode**: See `docs/WEATHER_DEMO_VERBOSE_MODE.md`

---

## Contributing

To add a new demo to both scripts:

1. Create demo file in `samples/`
2. Update `scripts/run_all_demos.sh`
3. Update `scripts/run_all_demos.py`
4. Test both scripts
5. Update documentation

---

## Conclusion

Both scripts provide excellent ways to run all demos:

- **Shell script**: Fast, minimal, Unix-focused
- **Python script**: Beautiful, cross-platform, extensible

Choose the one that best fits your needs! 🚀
