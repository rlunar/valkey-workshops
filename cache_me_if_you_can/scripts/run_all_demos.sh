#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Run All Demos Script
# This script executes all demo scripts in the samples folder sequentially

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SAMPLES_DIR="$PROJECT_ROOT/samples"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Running All Demo Scripts${NC}"
echo -e "${BLUE}========================================${NC}"
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

# Demo 3: Weather API Cache
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
if run_demo "Weather API Cache Demo" "demo_weather_api_cache.py"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
prompt_continue

# Demo 4: Semantic Search
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
echo -e "${YELLOW}Note: Semantic Search demo requires embeddings to be generated first${NC}"
if run_demo "Semantic Search Demo" "demo_semantic_search.py"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi
prompt_continue

# Demo 5: NLP to SQL
# TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
# echo -e "${YELLOW}Note: NLP to SQL demo requires Ollama to be running${NC}"
# if run_demo "NLP to SQL Demo" "demo_nlp_to_sql.py"; then
#     SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
# else
#     FAILED_DEMOS=$((FAILED_DEMOS + 1))
# fi
# prompt_continue

# Demo 6: Multi-threaded Performance Test
TOTAL_DEMOS=$((TOTAL_DEMOS + 1))
echo -e "${YELLOW}Running performance test with default settings (4 users, 10 queries)${NC}"
if run_demo "Multi-threaded Performance Test" "demo_multi_threaded_performance.py" "--users 4 --queries 10"; then
    SUCCESSFUL_DEMOS=$((SUCCESSFUL_DEMOS + 1))
else
    FAILED_DEMOS=$((FAILED_DEMOS + 1))
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Demo Execution Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total demos run: $TOTAL_DEMOS"
echo -e "${GREEN}Successful: $SUCCESSFUL_DEMOS${NC}"
if [ $FAILED_DEMOS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_DEMOS${NC}"
else
    echo -e "Failed: $FAILED_DEMOS"
fi
echo ""

if [ $FAILED_DEMOS -eq 0 ]; then
    echo -e "${GREEN}✓ All demos completed successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some demos failed. Check the output above for details.${NC}"
    exit 1
fi
