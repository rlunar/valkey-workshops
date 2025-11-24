#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Run All Demos Script
# This script executes all demo scripts in the samples folder sequentially
#
# Enhanced demos include:
# - Cache-Aside: Rich tables, verbose mode, interactive prompts
# - Write-Through: Consistency verification, detailed output
# - Write-Behind: Async operations, queue monitoring
# - Weather API: Country flags 🇺🇸, weather emojis ☀️, syntax-highlighted JSON
# - Multi-threaded: Performance metrics, JSON output, visualization support
#
# Usage:
#   ./scripts/run_all_demos.sh              # Run all demos with default settings
#   ./scripts/run_all_demos.sh --help       # Show this help message
#
# Individual demo options:
#   Weather API: --verbose, --interactive, --flush, --ttl, --cities
#   Multi-threaded: --users, --queries, --output
#   Cache demos: --interactive, --verbose, --flush

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Show help if requested
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo -e "${CYAN}Run All Demos Script${NC}"
    echo ""
    echo "This script runs all cache pattern demonstrations sequentially."
    echo ""
    echo -e "${CYAN}Usage:${NC}"
    echo "  ./scripts/run_all_demos.sh              # Run all demos"
    echo "  ./scripts/run_all_demos.sh --help       # Show this help"
    echo ""
    echo -e "${CYAN}Demos included:${NC}"
    echo "  1. Cache-Aside Pattern       - Read-through caching with lazy loading"
    echo "  2. Write-Through Cache       - Synchronous write to DB and cache"
    echo "  3. Write-Behind Cache        - Asynchronous write with queue"
    echo "  4. Weather API Cache         - Real-world API caching with emojis"
    echo "  5. Semantic Search           - Vector similarity search"
    echo "  6. Multi-threaded Performance - Concurrent load testing"
    echo ""
    echo -e "${CYAN}Enhanced features:${NC}"
    echo "  • Rich terminal formatting with colors and tables"
    echo "  • Country flags 🇺🇸 🇲🇽 🇬🇧 and weather emojis ☀️ 🌧️ ⛅"
    echo "  • Syntax-highlighted JSON output"
    echo "  • Interactive and verbose modes"
    echo "  • Performance metrics and visualizations"
    echo ""
    echo -e "${CYAN}Individual demo usage:${NC}"
    echo "  uv run samples/demo_weather_api_cache.py -v -c 5"
    echo "  uv run samples/demo_cache_aside.py -i -v"
    echo "  uv run samples/demo_multi_threaded_performance.py --threads 8 --queries 5000"
    echo ""
    exit 0
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SAMPLES_DIR="$PROJECT_ROOT/samples"

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Running All Cache Pattern Demos      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Enhanced with:${NC} Rich formatting, emojis, and interactive modes"
echo ""

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}✗ Error: .env file not found${NC}"
    echo -e "${YELLOW}  Please copy .env.example to .env and configure it${NC}"
    exit 1
fi

# Function to run a demo
run_demo() {
    local demo_name=$1
    local demo_file=$2
    local demo_args=${3:-""}
    
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Running: $demo_name${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [ ! -f "$SAMPLES_DIR/$demo_file" ]; then
        echo -e "${RED}✗ Demo file not found: $demo_file${NC}"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    
    if uv run "$SAMPLES_DIR/$demo_file" $demo_args; then
        echo -e "${GREEN}✓ $demo_name completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ $demo_name failed${NC}"
        return 1
    fi
}

# Function to prompt user to continue
prompt_continue() {
    echo ""
    read -p "Press Enter to continue to next demo (or Ctrl+C to exit)..."
    echo ""
}

# Track results
TOTAL_DEMOS=0
SUCCESSFUL_DEMOS=0
FAILED_DEMOS=0

# Demo 1: Cache-Aside Pattern
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
if run_demo "Cache-Aside Pattern Demo" "demo_cache_aside.py"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
prompt_continue

# Demo 2: Write-Through Cache Pattern
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
if run_demo "Write-Through Cache Pattern Demo" "demo_write_through_cache.py"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
prompt_continue

# Demo 3: Write-Behind Cache Pattern
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
if run_demo "Write-Behind Cache Pattern Demo" "demo_write_behind_cache.py"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
prompt_continue

# Demo 4: Weather API Cache
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
echo -e "${YELLOW}Running Weather API Cache demo with 5 cities and 15-minute TTL${NC}"
echo -e "${YELLOW}Features: Country flags 🇺🇸 🇲🇽 🇬🇧, weather emojis ☀️ 🌧️ ⛅, and cache performance${NC}"
if run_demo "Weather API Cache Demo" "demo_weather_api_cache.py" "--cities 5 --ttl 15"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
echo -e "${BLUE}💡 Tip: Try with --verbose flag to see cache keys and JSON samples${NC}"
echo -e "${BLUE}   Example: uv run samples/demo_weather_api_cache.py -v -c 5${NC}"
prompt_continue

# Demo 5: Semantic Search
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
echo -e "${YELLOW}Note: Semantic Search demo requires embeddings to be generated first${NC}"
if run_demo "Semantic Search Demo" "demo_semantic_search.py"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
prompt_continue

# Demo 6: NLP to SQL
# TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
# echo -e "${YELLOW}Note: NLP to SQL demo requires Ollama to be running${NC}"
# if run_demo "NLP to SQL Demo" "demo_nlp_to_sql.py"; then
#     SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
# else
#     FAILED_DEMOS=$((FAILED_DEMOS + 1))
# fi
# prompt_continue

# Demo 7: Multi-threaded Performance Test
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
echo -e "${YELLOW}Running multi-threaded performance test (4 threads, 1000 queries each)${NC}"
echo -e "${YELLOW}This will test cache performance under concurrent load${NC}"
if run_demo "Multi-threaded Performance Test" "demo_multi_threaded_performance.py" "--threads 4 --queries 1000"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
echo -e "${BLUE}💡 Tip: Results saved to logs/ directory with timestamp${NC}"
echo -e "${BLUE}   View with: uv run samples/plot_time_series.py logs/perf_test_*.json${NC}"

# Summary
echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Demo Execution Summary                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total demos run:    ${BLUE}$TOTAL_DEMOS${NC}"
echo -e "Successful:         ${GREEN}$SUCCESSFUL_DEMOS ✓${NC}"
if [ $FAILED_DEMOS -gt 0 ]; then
    echo -e "Failed:             ${RED}$FAILED_DEMOS ✗${NC}"
else
    echo -e "Failed:             $FAILED_DEMOS"
fi
echo ""

if [ $FAILED_DEMOS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ All demos completed successfully!  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo -e "  • Try demos with ${YELLOW}--verbose${NC} flag for detailed output"
    echo -e "  • Use ${YELLOW}--interactive${NC} mode to step through each phase"
    echo -e "  • Check ${YELLOW}logs/${NC} directory for performance test results"
    echo -e "  • Run ${YELLOW}./scripts/run_all_demos.sh --help${NC} for more options"
    echo ""
    exit 0
else
    echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠ Some demos failed                  ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "  • Check that Valkey/Redis is running"
    echo -e "  • Verify .env configuration"
    echo -e "  • Review error messages above"
    echo -e "  • Try running failed demos individually"
    echo ""
    exit 1
fi
