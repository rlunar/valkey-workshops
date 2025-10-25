#!/bin/bash

# Flughafen DB - Complete Database Setup Script
# This script resets the database and imports all data from OpenFlights.org

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "models" ] || [ ! -d "scripts" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    echo "Please copy .env.example to .env and configure your database settings:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your database credentials"
    exit 1
fi

print_header "Flughafen DB Complete Setup"
echo "This script will:"
echo "  1. Reset the database (DROP ALL TABLES)"
echo "  2. Download and import countries data"
echo "  3. Download and import airports data"
echo "  4. Download and import airlines data"
echo "  5. Download and import aircraft types data"
echo
print_warning "This will DELETE ALL EXISTING DATA in your database!"
echo

# Confirm with user
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Operation cancelled by user"
    exit 0
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed or not in PATH"
    echo "Please install uv first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if Python dependencies are available
print_status "Checking dependencies..."
if ! uv run python -c "import sqlmodel, polars, requests, tqdm, dotenv" 2>/dev/null; then
    print_warning "Dependencies not found. Installing..."
    uv sync
    if [ $? -ne 0 ]; then
        print_error "Failed to install dependencies"
        exit 1
    fi
    print_success "Dependencies installed successfully"
else
    print_success "Dependencies are available"
fi

# Step 1: Reset Database
print_header "Step 1: Resetting Database"
print_status "Dropping all existing tables and creating fresh schema..."

echo "y" | uv run python scripts/reset_database.py
if [ $? -ne 0 ]; then
    print_error "Database reset failed"
    exit 1
fi
print_success "Database reset completed"

# Step 2: Download Countries
print_header "Step 2: Importing Countries Data"
print_status "Downloading and importing countries from OpenFlights.org..."

echo "y" | uv run python scripts/download_countries.py
if [ $? -ne 0 ]; then
    print_error "Countries import failed"
    exit 1
fi
print_success "Countries data imported successfully"

# Step 3: Download Airports
print_header "Step 3: Importing Airports Data"
print_status "Downloading and importing airports from OpenFlights.org..."

echo "y" | uv run python scripts/download_airports.py
if [ $? -ne 0 ]; then
    print_error "Airports import failed"
    exit 1
fi
print_success "Airports data imported successfully"

# Step 4: Download Airlines
print_header "Step 4: Importing Airlines Data"
print_status "Downloading and importing airlines from OpenFlights.org..."

echo "y" | uv run python scripts/download_airlines.py
if [ $? -ne 0 ]; then
    print_error "Airlines import failed"
    exit 1
fi
print_success "Airlines data imported successfully"

# Step 5: Download Aircraft Types
print_header "Step 5: Importing Aircraft Types Data"
print_status "Downloading and importing aircraft types from OpenFlights.org..."

echo "y" | uv run python scripts/download_planes.py
if [ $? -ne 0 ]; then
    print_error "Aircraft types import failed"
    exit 1
fi
print_success "Aircraft types data imported successfully"

# Final Summary
print_header "Setup Complete!"
print_success "Database setup completed successfully!"
echo
echo "Your Flughafen DB now contains:"
echo "  ✓ Countries data (~260 countries with ISO codes)"
echo "  ✓ Airports data (~7,700 airports worldwide)"
echo "  ✓ Airlines data (~6,100+ airlines)"
echo "  ✓ Aircraft types data (~246 aircraft types)"
echo
echo "Next steps:"
echo "  • Run validation: uv run python scripts/validate_models.py"
echo "  • View statistics: uv run python scripts/airlines_stats.py"
echo "  • View aircraft stats: uv run python scripts/planes_stats.py"
echo "  • Try examples: uv run python scripts/database_example.py"
echo
print_success "Happy coding! ✈️"