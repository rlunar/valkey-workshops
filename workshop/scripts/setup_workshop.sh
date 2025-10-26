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
echo "  3. Download and import cities data (optional)"
echo "  4. Download and import aircraft types data"
echo "  5. Download and import airlines data"
echo "  6. Download and import airports data"
echo "  7. Download and import routes data"
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

# Step 3: Download Cities
print_header "Step 3: Importing Cities Data"
print_status "Downloading city population data from GeoNames for flight planning..."
echo "This will download ~160k cities with population data for flight frequency planning."
echo "It may take several minutes to download and process."
echo

print_status "Downloading and importing cities from GeoNames..."

# Use cities15000 dataset for good balance of coverage and performance
uv run python scripts/download_cities.py --dataset cities15000 --verbose
if [ $? -ne 0 ]; then
    print_error "Cities import failed"
    exit 1
fi
print_success "Cities data imported successfully"

# Step 4: Download Aircraft Types (Airplanes)
print_header "Step 4: Importing Aircraft Types Data"
print_status "Downloading and importing aircraft types from OpenFlights.org..."

echo "y" | uv run python scripts/download_planes.py
if [ $? -ne 0 ]; then
    print_error "Aircraft types import failed"
    exit 1
fi
print_success "Aircraft types data imported successfully"

# Step 5: Download Airlines
print_header "Step 5: Importing Airlines Data"
print_status "Downloading and importing airlines from OpenFlights.org..."

echo "y" | uv run python scripts/download_airlines.py
if [ $? -ne 0 ]; then
    print_error "Airlines import failed"
    exit 1
fi
print_success "Airlines data imported successfully"

# Step 6: Download Airports
print_header "Step 6: Importing Airports Data"
print_status "Downloading and importing airports from OpenFlights.org..."

echo "y" | uv run python scripts/download_airports.py
if [ $? -ne 0 ]; then
    print_error "Airports import failed"
    exit 1
fi
print_success "Airports data imported successfully"

# Step 7: Create City-Airport Relations
print_header "Step 7: Creating City-Airport Relationships"

# Check if cities were imported
cities_imported=$(uv run python -c "
import sys, os
sys.path.append('.')
from models.database import DatabaseManager
from sqlmodel import Session, select, func
from models.city import City
try:
    db = DatabaseManager()
    with Session(db.engine) as session:
        count = session.exec(select(func.count(City.city_id))).first()
        print(count if count else 0)
except:
    print(0)
" 2>/dev/null)

if [ "$cities_imported" -gt 0 ]; then
    print_status "Creating relationships between cities and airports..."
    echo "This step maps airports to nearby cities for flight planning analysis."
    echo
    
    uv run python scripts/create_city_airport_relations.py --max-distance 100
    if [ $? -ne 0 ]; then
        print_warning "City-airport relationships creation failed, but continuing..."
    else
        print_success "City-airport relationships created successfully"
    fi
else
    print_status "Skipping city-airport relationships (cities not imported)"
fi

# Step 8: Download Routes
print_header "Step 8: Importing Routes Data"
print_status "Downloading and importing routes from OpenFlights.org..."

echo "y" | uv run python scripts/download_routes.py
if [ $? -ne 0 ]; then
    print_error "Routes import failed"
    exit 1
fi
print_success "Routes data imported successfully"

# Final Summary
print_header "Setup Complete!"
print_success "Database setup completed successfully!"
echo
echo "Your Flughafen DB now contains:"
echo "  ✓ Countries data (~260 countries with ISO codes)"
echo "  ✓ Aircraft types data (~246 aircraft types)"
echo "  ✓ Airlines data (~6,100+ airlines)"
echo "  ✓ Airports data (~7,700 airports worldwide)"
echo "  ✓ Routes data (~67,600+ routes between airports)"

# Check if cities and city-airport relations were imported
uv run python -c "
import sys, os
sys.path.append('.')
from models.database import DatabaseManager
from sqlmodel import Session, select, func
from models.city import City, CityAirportRelation
try:
    db = DatabaseManager()
    with Session(db.engine) as session:
        city_count = session.exec(select(func.count(City.city_id))).first()
        relation_count = session.exec(select(func.count(CityAirportRelation.relation_id))).first()
        
        if city_count and city_count > 0:
            print(f'  ✓ Cities data (~{city_count:,} cities with population data)')
            if relation_count and relation_count > 0:
                print(f'  ✓ City-airport relationships (~{relation_count:,} relationships)')
            else:
                print('  • City-airport relationships (not created - run scripts/create_city_airport_relations.py)')
        else:
            print('  • Cities data (not imported - run scripts/download_cities.py)')
            print('  • City-airport relationships (requires cities data)')
except Exception as e:
    print('  • Cities data (not imported - run scripts/download_cities.py)')
    print('  • City-airport relationships (requires cities data)')
" 2>/dev/null

echo
echo "Next steps:"
echo "  • Run validation: uv run python scripts/validate_models.py"
echo "  • View statistics: uv run python scripts/airlines_stats.py"
echo "  • View aircraft stats: uv run python scripts/planes_stats.py"
echo "  • View route stats: uv run python scripts/routes_stats.py"
echo "  • Try examples: uv run python scripts/database_example.py"
echo "  • Try route examples: uv run python scripts/route_example.py"
if uv run python -c "
import sys, os
sys.path.append('.')
from models.database import DatabaseManager
from sqlmodel import Session, select, func
from models.city import City, CityAirportRelation
try:
    db = DatabaseManager()
    with Session(db.engine) as session:
        city_count = session.exec(select(func.count(City.city_id))).first()
        relation_count = session.exec(select(func.count(CityAirportRelation.relation_id))).first()
        
        if city_count and city_count > 0:
            print('cities')
            if relation_count and relation_count > 0:
                print('relations')
        exit(0)
except:
    exit(1)
" 2>/dev/null; then
    output=$(uv run python -c "
import sys, os
sys.path.append('.')
from models.database import DatabaseManager
from sqlmodel import Session, select, func
from models.city import City, CityAirportRelation
try:
    db = DatabaseManager()
    with Session(db.engine) as session:
        city_count = session.exec(select(func.count(City.city_id))).first()
        relation_count = session.exec(select(func.count(CityAirportRelation.relation_id))).first()
        
        if city_count and city_count > 0:
            print('cities')
            if relation_count and relation_count > 0:
                print('relations')
except:
    pass
" 2>/dev/null)
    
    if echo "$output" | grep -q "cities"; then
        echo "  • Analyze cities: uv run python scripts/cities_flight_analysis.py"
        echo "  • City examples: uv run python scripts/city_example.py"
        
        if echo "$output" | grep -q "relations"; then
            echo "  • City-airport analysis: uv run python scripts/city_airport_analysis.py"
        else
            echo "  • Create city-airport relationships: uv run python scripts/create_city_airport_relations.py"
        fi
    fi
fi
echo
print_success "Happy coding! ✈️"