#!/bin/bash
# Test script to demonstrate the --verbose flag

echo "=========================================="
echo "Testing --verbose flag"
echo "=========================================="
echo ""

echo "1. Demo mode with verbose (shows first query prompt):"
echo "   python daos/nlp_to_sql.py --verbose"
echo ""

echo "2. Interactive mode with verbose:"
echo "   python daos/nlp_to_sql.py --verbose interactive"
echo ""

echo "3. With specific model and verbose:"
echo "   python daos/nlp_to_sql.py tinyllama --verbose"
echo ""

echo "4. All flags together:"
echo "   python daos/nlp_to_sql.py codellama --verbose interactive"
echo ""

echo "Note: The --verbose flag can also be shortened to -v"
echo "      Example: python daos/nlp_to_sql.py -v"
