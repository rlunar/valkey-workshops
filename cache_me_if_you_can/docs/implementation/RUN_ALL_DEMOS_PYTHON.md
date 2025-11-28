# Run All Demos - Python Version

## Overview
Python implementation of the run_all_demos script using Typer and Rich for a beautiful, interactive CLI experience.

## Features

### 1. Professional CLI with Typer
- Clean command-line interface
- Built-in help system
- Type-safe arguments
- Auto-completion support

### 2. Beautiful Output with Rich
- Color-coded messages
- Formatted tables and panels
- Progress indicators
- Box drawing characters

### 3. Demo Management
- Tracks success/failure for each demo
- Shows detailed results summary
- Provides helpful tips after each demo
- Handles errors gracefully

### 4. Interactive Mode
- Prompts between demos (default)
- Skip prompts with `--skip-prompts` flag
- Confirmation dialogs
- User-friendly experience

## Usage

### Basic Usage
```bash
# Using uv (recommended)
uv run scripts/run_all_demos.py

# Using python directly
python scripts/run_all_demos.py

# Using the venv
.venv/bin/python scripts/run_all_demos.py
```

### Command-Line Options

#### Show Help
```bash
python scripts/run_all_demos.py --help
```

#### Skip Prompts (Non-Interactive)
```bash
python scripts/run_all_demos.py --skip-prompts

# Short form
python scripts/run_all_demos.py -y
```

#### Verbose Mode (Future)
```bash
python scripts/run_all_demos.py --verbose

# Short form
python scripts/run_all_demos.py -v
```

## Output Examples

### Header
```
╔══════════════════════════════════════════════════════════╗
║  Running All Cache Pattern Demos                        ║
║  Enhanced with Rich formatting, emojis, and interactive  ║
╚══════════════════════════════════════════════════════════╝
```

### Demo Execution
```
╔══════════════════════════════════════════════════════════╗
║  Cache-Aside Pattern Demo                               ║
╚══════════════════════════════════════════════════════════╝

Demonstrates read-through caching with lazy loading

⠹ Running Cache-Aside Pattern Demo...

✓ Cache-Aside Pattern Demo completed successfully
💡 Tip: Try with --interactive and --verbose flags for detailed output

Continue to next demo? [Y/n]:
```

### Summary (All Success)
```
╔══════════════════════════════════════════════════════════╗
║  Demo Execution Summary                                  ║
╚══════════════════════════════════════════════════════════╝

┌─────────────────┬────────┐
│ Total demos run │ 6      │
│ Successful      │ 6 ✓    │
│ Failed          │ 0      │
└─────────────────┴────────┘

╔══════════════════════════════════════════════════════════╗
║  ✓ All demos completed successfully!                    ║
║                                                          ║
║  Next steps:                                             ║
║    • Try demos with --verbose flag for detailed output  ║
║    • Use --interactive mode to step through each phase  ║
║    • Check logs/ directory for performance test results ║
║    • Run python scripts/run_all_demos.py --help         ║
╚══════════════════════════════════════════════════════════╝
```

### Summary (With Failures)
```
╔══════════════════════════════════════════════════════════╗
║  Demo Execution Summary                                  ║
╚══════════════════════════════════════════════════════════╝

┌─────────────────┬────────┐
│ Total demos run │ 6      │
│ Successful      │ 5 ✓    │
│ Failed          │ 1 ✗    │
└─────────────────┴────────┘

Detailed Results
┌────────────────────────────┬──────────┬─────────────────┐
│ Demo                       │ Status   │ Details         │
├────────────────────────────┼──────────┼─────────────────┤
│ Cache-Aside Pattern Demo   │ ✓ SUCCESS│                 │
│ Write-Through Cache Demo   │ ✓ SUCCESS│                 │
│ Write-Behind Cache Demo    │ ✓ SUCCESS│                 │
│ Weather API Cache Demo     │ ✓ SUCCESS│                 │
│ Semantic Search Demo       │ ✗ FAILED │ Exit code 1     │
│ Multi-threaded Perf Test   │ ✓ SUCCESS│                 │
└────────────────────────────┴──────────┴─────────────────┘

╔══════════════════════════════════════════════════════════╗
║  ⚠ Some demos failed                                    ║
║                                                          ║
║  Troubleshooting:                                        ║
║    • Check that Valkey/Redis is running                 ║
║    • Verify .env configuration                          ║
║    • Review error messages above                        ║
║    • Try running failed demos individually              ║
╚══════════════════════════════════════════════════════════╝
```

## Implementation Details

### DemoRunner Class
Manages demo execution and result tracking:

```python
class DemoRunner:
    def __init__(self, skip_prompts: bool = False)
    def run_demo(name, script, args, description, tip) -> bool
    def prompt_continue()
    def print_summary()
```

**Features:**
- Tracks total, successful, and failed demos
- Stores detailed results for each demo
- Handles subprocess execution
- Shows progress indicators
- Provides helpful tips

### Demo Configuration
Each demo is configured with:
- **name**: Display name
- **script**: Python file in samples/
- **args**: Command-line arguments (optional)
- **description**: Brief explanation
- **tip**: Helpful suggestion (optional)

### Error Handling
- Checks for .env file existence
- Validates demo file paths
- Captures subprocess errors
- Provides detailed error messages
- Exits with appropriate status code

## Demos Included

### 1. Cache-Aside Pattern
```python
runner.run_demo(
    name="Cache-Aside Pattern Demo",
    script="demo_cache_aside.py",
    description="Demonstrates read-through caching with lazy loading",
    tip="Try with --interactive and --verbose flags"
)
```

### 2. Write-Through Cache
```python
runner.run_demo(
    name="Write-Through Cache Pattern Demo",
    script="demo_write_through_cache.py",
    description="Shows synchronous writes to both database and cache",
    tip="Watch for consistency verification"
)
```

### 3. Write-Behind Cache
```python
runner.run_demo(
    name="Write-Behind Cache Pattern Demo",
    script="demo_write_behind_cache.py",
    description="Demonstrates asynchronous writes with queue processing",
    tip="Observe queue monitoring and batch processing"
)
```

### 4. Weather API Cache
```python
runner.run_demo(
    name="Weather API Cache Demo",
    script="demo_weather_api_cache.py",
    args=["--cities", "5", "--ttl", "15"],
    description="Real-world API caching with flags 🇺🇸 and emojis ☀️",
    tip="Run with --verbose to see cache keys and JSON"
)
```

### 5. Semantic Search
```python
runner.run_demo(
    name="Semantic Search Demo",
    script="demo_semantic_search.py",
    description="Vector similarity search with embeddings",
    tip="Generate embeddings first if this demo fails"
)
```

### 6. Multi-threaded Performance
```python
runner.run_demo(
    name="Multi-threaded Performance Test",
    script="demo_multi_threaded_performance.py",
    args=["--users", "4", "--queries", "10"],
    description="Tests cache performance under concurrent load",
    tip="Results in logs/. View with plot_time_series.py"
)
```

## Advantages Over Shell Script

### 1. Cross-Platform
- Works on Windows, macOS, and Linux
- No bash dependency
- Consistent behavior across platforms

### 2. Better Error Handling
- Python exception handling
- Detailed error messages
- Graceful degradation

### 3. Rich Output
- Beautiful formatting with Rich library
- Progress indicators
- Interactive prompts
- Color-coded messages

### 4. Type Safety
- Typer provides type checking
- Auto-completion support
- Better IDE integration

### 5. Extensibility
- Easy to add new demos
- Simple to customize behavior
- Reusable DemoRunner class

## Comparison: Shell vs Python

| Feature | Shell Script | Python Script |
|---------|-------------|---------------|
| Cross-platform | ❌ Unix only | ✅ All platforms |
| Rich formatting | ⚠️ Basic colors | ✅ Full Rich support |
| Progress indicators | ❌ None | ✅ Spinners |
| Error handling | ⚠️ Basic | ✅ Comprehensive |
| Type safety | ❌ None | ✅ Typer types |
| Interactive prompts | ✅ read command | ✅ Rich prompts |
| Extensibility | ⚠️ Moderate | ✅ Easy |
| Dependencies | ✅ None | ⚠️ Python + packages |

## Future Enhancements

### Planned Features
1. **Verbose Mode**: Show detailed output from each demo
2. **Select Demos**: Run specific demos only
3. **Parallel Execution**: Run independent demos concurrently
4. **Report Generation**: Create HTML/PDF reports
5. **Configuration File**: Customize demo settings
6. **Dry Run**: Show what would be executed
7. **Timing Statistics**: Track execution time per demo

### Example Future Usage
```bash
# Run specific demos
python scripts/run_all_demos.py --demos cache-aside,weather

# Parallel execution
python scripts/run_all_demos.py --parallel

# Generate report
python scripts/run_all_demos.py --report html

# Dry run
python scripts/run_all_demos.py --dry-run
```

## Troubleshooting

### Import Errors
```bash
# Install dependencies
uv sync

# Or use pip
pip install typer rich
```

### Permission Denied
```bash
# Make executable
chmod +x scripts/run_all_demos.py
```

### Demo Failures
- Check Valkey/Redis is running
- Verify .env configuration
- Review error messages in output
- Run failed demos individually for details

## Contributing

To add a new demo:

1. Add demo file to `samples/` directory
2. Update `main()` function in `run_all_demos.py`:

```python
runner.run_demo(
    name="My New Demo",
    script="demo_my_new_feature.py",
    args=["--option", "value"],  # optional
    description="Brief description",
    tip="Helpful tip for users"  # optional
)
runner.prompt_continue()
```

3. Test the script:
```bash
python scripts/run_all_demos.py
```

## Conclusion

The Python version provides a modern, cross-platform alternative to the shell script with:
- ✅ Beautiful Rich formatting
- ✅ Interactive prompts
- ✅ Comprehensive error handling
- ✅ Detailed result tracking
- ✅ Helpful tips and suggestions
- ✅ Professional appearance

Perfect for showcasing the enhanced demo suite! 🎉
