# Scripts Fix - Multi-threaded Performance Demo

## Issue
The run_all_demos scripts were using incorrect command-line arguments for the multi-threaded performance demo.

### Error
```
No such option: --users (Possible options: --queries, --verbose)
```

## Root Cause
The multi-threaded performance demo uses `--threads` not `--users` for specifying concurrent threads.

## Actual Options
From `demo_multi_threaded_performance.py --help`:

```
--threads    -t    Number of concurrent threads to simulate [default: 4]
--queries    -q    Number of queries per thread [default: 10000]
--read-ratio -r    Percentage of read operations (0-100) [default: 80]
--ttl              Cache TTL in milliseconds [default: 300000]
--random           Use random passenger IDs (all passengers)
--interactive -i   Run in interactive mode with prompts
--verbose    -v    Show SQL query and cache key format
--flush      -f    Flush Valkey cache before running test
```

## Changes Made

### 1. Shell Script (`scripts/run_all_demos.sh`)

**Before:**
```bash
run_demo "Multi-threaded Performance Test" "demo_multi_threaded_performance.py" "--users 4 --queries 10"
```

**After:**
```bash
run_demo "Multi-threaded Performance Test" "demo_multi_threaded_performance.py" "--threads 4 --queries 1000"
```

**Also updated help text:**
```bash
# Before
uv run samples/demo_multi_threaded_performance.py --users 8 --queries 20

# After
uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000
```

### 2. Python Script (`scripts/run_all_demos.py`)

**Before:**
```python
runner.run_demo(
    name="Multi-threaded Performance Test",
    script="demo_multi_threaded_performance.py",
    args=["--users", "4", "--queries", "10"],
    description="Tests cache performance under concurrent load (4 users, 10 queries each)",
    tip="Results saved to logs/ directory..."
)
```

**After:**
```python
runner.run_demo(
    name="Multi-threaded Performance Test",
    script="demo_multi_threaded_performance.py",
    args=["--threads", "4", "--queries", "1000"],
    description="Tests cache performance under concurrent load (4 threads, 1000 queries each)",
    tip="Results saved to logs/ directory..."
)
```

**Also updated docstring examples:**
```python
# Before
uv run samples/demo_multi_threaded_performance.py --users 8 --queries 20

# After
uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000
```

## Query Count Adjustment

Changed from 10 queries to 1000 queries per thread for more realistic performance testing:
- **Old**: 4 threads × 10 queries = 40 total queries (too few)
- **New**: 4 threads × 1000 queries = 4000 total queries (better for testing)

This provides more meaningful performance metrics while still completing quickly.

## Testing

### Verify the fix works:

**Shell script:**
```bash
./scripts/run_all_demos.sh
```

**Python script:**
```bash
python scripts/run_all_demos.py
```

**Individual demo:**
```bash
uv run samples/demo_multi_threaded_performance.py --threads 4 --queries 1000
```

## Correct Usage Examples

### Basic Test
```bash
uv run samples/demo_multi_threaded_performance.py
# Uses defaults: 4 threads, 10000 queries per thread
```

### Custom Load
```bash
# Light load
uv run samples/demo_multi_threaded_performance.py --threads 2 --queries 500

# Medium load (used in scripts)
uv run samples/demo_multi_threaded_performance.py --threads 4 --queries 1000

# Heavy load
uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000

# High concurrency
uv run samples/demo_multi_threaded_performance.py --threads 20 --queries 10000
```

### With Options
```bash
# Interactive mode
uv run samples/demo_multi_threaded_performance.py -i -v -f

# Write-heavy workload
uv run samples/demo_multi_threaded_performance.py --threads 10 --queries 5000 --read-ratio 30

# Random passenger mode
uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000 --random
```

## Summary

✅ Fixed `--users` → `--threads` in both scripts
✅ Updated query count from 10 → 1000 for better testing
✅ Updated all documentation and help text
✅ Verified scripts work correctly

The multi-threaded performance demo now runs successfully in both scripts! 🎉
