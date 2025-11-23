#!/bin/bash

# Run Airport App with Streamlit
# This script uses uv to manage dependencies and run the Streamlit application

set -e

echo "=========================================="
echo "Starting Airport App with Streamlit"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo "   ✓ Created .env file"
    echo "   Please edit .env with your database and cache credentials"
    echo ""
fi

# Check if database is accessible
echo "Checking database connection..."
DB_HOST=$(grep DB_HOST .env | cut -d '=' -f2)
DB_PORT=$(grep DB_PORT .env | cut -d '=' -f2)
DB_USER=$(grep DB_USER .env | cut -d '=' -f2)

if command -v mysql &> /dev/null; then
    if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -e "SELECT 1" &> /dev/null; then
        echo "✓ Database connection successful"
    else
        echo "⚠️  Warning: Cannot connect to database"
        echo "   Please check your database credentials in .env"
    fi
else
    echo "⚠️  mysql client not found, skipping database check"
fi

echo ""

# Check if cache is accessible
echo "Checking cache connection..."
CACHE_HOST=$(grep CACHE_HOST .env | cut -d '=' -f2)
CACHE_PORT=$(grep CACHE_PORT .env | cut -d '=' -f2)

if command -v redis-cli &> /dev/null; then
    if redis-cli -h "$CACHE_HOST" -p "$CACHE_PORT" ping &> /dev/null; then
        echo "✓ Cache connection successful"
    else
        echo "⚠️  Warning: Cannot connect to cache"
        echo "   Please check your cache is running"
    fi
elif command -v valkey-cli &> /dev/null; then
    if valkey-cli -h "$CACHE_HOST" -p "$CACHE_PORT" ping &> /dev/null; then
        echo "✓ Cache connection successful"
    else
        echo "⚠️  Warning: Cannot connect to cache"
        echo "   Please check your cache is running"
    fi
else
    echo "⚠️  redis-cli/valkey-cli not found, skipping cache check"
fi

echo ""
echo "=========================================="
echo "Launching Streamlit App..."
echo "=========================================="
echo ""
echo "The app will open in your browser at:"
echo "  http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the Streamlit app with uv
uv run streamlit run airport_app.py
