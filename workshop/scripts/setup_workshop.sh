#!/bin/bash

# Flughafen DB - Complete Database Setup Script
# This script resets the database and imports all data from OpenFlights.org
#
# Usage: ./setup_workshop.sh [-s] [-v]
#   -s    Step-by-step mode (interactive: Enter to continue, 's' to skip, 'q' to quit)
#   -v    Verbose mode (show detailed output)

set -e  # Exit on any error

# Parse command line arguments
STEP_BY_STEP=false
VERBOSE=false
while getopts "sv" opt; do
    case $opt in
        s)
            STEP_BY_STEP=true
            ;;
        v)
            VERBOSE=true
            ;;
        \?)
            echo "Usage: $0 [-s] [-v]"
            echo "  -s    Step-by-step mode (interactive: Enter to continue, 's' to skip, 'q' to quit)"
            echo "  -v    Verbose mode (show detailed output)"
            exit 1
            ;;
    esac
done

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

# Function to wait for user confirmation in step-by-step mode
wait_for_confirmation() {
    if [ "$STEP_BY_STEP" = true ]; then
        echo
        while true; do
            read -p "Press Enter to continue, 's' to skip this step, or 'q' to quit: " -r
            case $REPLY in
                "")
                    echo
                    return 0  # Continue with the step
                    ;;
                [Ss])
                    echo
                    print_warning "Skipping this step..."
                    return 1  # Skip the step
                    ;;
                [Qq])
                    echo
                    print_status "Setup cancelled by user"
                    exit 0
                    ;;
                *)
                    echo "Invalid option. Press Enter to continue, 's' to skip, or 'q' to quit."
                    ;;
            esac
        done
    fi
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
echo "  8. Populate aircraft fleets"
echo "  9. Populate flight schedules (2025 & first half 2026, max 1000 flights/day)"
echo "  10. Populate passenger data (up to 1 million passengers)"
echo "  11. Populate flight bookings (max 100 bookings per passenger)"
echo
if [ "$STEP_BY_STEP" = true ]; then
    print_status "Running in step-by-step mode - you can skip steps or quit at any time"
fi
if [ "$VERBOSE" = true ]; then
    print_status "Running in verbose mode - detailed output will be shown"
fi
if [ "$STEP_BY_STEP" = false ]; then
    print_warning "This will DELETE ALL EXISTING DATA in your database!"
    echo
    
    # Confirm with user in non-interactive mode
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Operation cancelled by user"
        exit 0
    fi
else
    print_warning "Step 1 will DELETE ALL EXISTING DATA in your database!"
    print_status "You can skip the database reset step if you want to keep existing data."
    echo
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

if wait_for_confirmation; then
    uv run python scripts/reset_database.py --yes
    if [ $? -ne 0 ]; then
        print_error "Database reset failed"
        exit 1
    fi
    print_success "Database reset completed"
fi

# Step 2: Download Countries
print_header "Step 2: Importing Countries Data"
print_status "Downloading and importing countries from OpenFlights.org..."

if wait_for_confirmation; then
    uv run python scripts/download_countries.py --yes
    if [ $? -ne 0 ]; then
        print_error "Countries import failed"
        exit 1
    fi
    print_success "Countries data imported successfully"
fi

# Step 3: Download Cities
print_header "Step 3: Importing Cities Data"
print_status "Downloading city population data from GeoNames for flight planning..."
echo "This will download ~160k cities with population data for flight frequency planning."
echo "It may take several minutes to download and process."
echo

if wait_for_confirmation; then
    print_status "Downloading and importing cities from GeoNames..."

    # Use cities15000 dataset for good balance of coverage and performance
    uv run python scripts/download_cities.py --dataset cities15000 --verbose
    if [ $? -ne 0 ]; then
        print_error "Cities import failed"
        exit 1
    fi
    print_success "Cities data imported successfully"
fi

# Step 4: Download Aircraft Types (Airplanes)
print_header "Step 4: Importing Aircraft Types Data"
print_status "Downloading and importing aircraft types from OpenFlights.org..."

if wait_for_confirmation; then
    uv run python scripts/download_planes.py --yes
    if [ $? -ne 0 ]; then
        print_error "Aircraft types import failed"
        exit 1
    fi
    print_success "Aircraft types data imported successfully"
fi

# Step 5: Download Airlines
print_header "Step 5: Importing Airlines Data"
print_status "Downloading and importing airlines from OpenFlights.org..."

if wait_for_confirmation; then
    uv run python scripts/download_airlines.py --yes
    if [ $? -ne 0 ]; then
        print_error "Airlines import failed"
        exit 1
    fi
    print_success "Airlines data imported successfully"
fi

# Step 6: Download Airports
print_header "Step 6: Importing Airports Data"
print_status "Downloading and importing airports from OpenFlights.org..."

if wait_for_confirmation; then
    echo "y" | uv run python scripts/download_airports.py --yes
    if [ $? -ne 0 ]; then
        print_error "Airports import failed"
        exit 1
    fi
    print_success "Airports data imported successfully"
fi

# Step 7: Create City-Airport Relations
print_header "Step 7: Creating City-Airport Relationships"

if wait_for_confirmation; then
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
fi

# Step 8: Download Routes
print_header "Step 8: Importing Routes Data"
print_status "Downloading and importing routes from OpenFlights.org..."

if wait_for_confirmation; then
    if [ "$VERBOSE" = true ]; then
        echo "y" | uv run python scripts/download_routes.py --yes --verbose
    else
        echo "y" | uv run python scripts/download_routes.py --yes
    fi
    if [ $? -ne 0 ]; then
        print_error "Routes import failed"
        exit 1
    fi
    print_success "Routes data imported successfully"
fi

# Step 9: Populate Aircraft Fleets
print_header "Step 9: Populating Aircraft Fleets"
print_status "Generating realistic aircraft fleets for airlines..."
echo "This step creates aircraft instances for each airline based on their characteristics."
echo "Fleet sizes are optimized for realistic airline operations with proper capacity distribution."
echo

if wait_for_confirmation; then
    uv run python scripts/populate_aircraft.py --reset-db --fleet-multiplier 0.3
    if [ $? -ne 0 ]; then
        print_error "Aircraft fleet population failed"
        exit 1
    fi
    print_success "Aircraft fleets populated successfully"
fi

# Step 10: Populate Flight Schedules
print_header "Step 10: Populating Flight Schedules"
print_status "Generating flight schedules based on routes and flight rules..."
echo "This step creates realistic flight schedules prioritizing major hub airports."
echo "Aircraft selection is optimized for route distance and passenger demand."
echo "This may take several minutes depending on the number of routes."
echo

if wait_for_confirmation; then
    # Ask user which flight population method to use
    echo "Choose flight population method:"
    echo "  1) Realistic - Hub-prioritized flight generation (recommended)"
    echo "  2) Comprehensive - Advanced flight generation with detailed rules"
    echo "  3) Simple - Basic flight generation (faster, less realistic)"
    echo
    read -p "Enter your choice (1-3, default: 1): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[3]$ ]]; then
        print_status "Using simple flight population..."
        uv run python scripts/populate_flights_simple.py --yes
    elif [[ $REPLY =~ ^[2]$ ]]; then
        print_status "Using comprehensive flight population..."
        uv run python scripts/populate_flights_comprehensive.py --no-reset
    else
        print_status "Using realistic hub-prioritized flight population (recommended)..."
        uv run python scripts/populate_flights_realistic.py --no-reset
    fi

    if [ $? -ne 0 ]; then
        print_error "Flight schedule population failed"
        exit 1
    fi
    print_success "Flight schedules populated successfully"
fi

# Step 11: Populate Passenger Data
print_header "Step 11: Populating Passenger Data"
print_status "Generating realistic passenger records with global distribution..."
echo "This step creates passenger records with realistic geographic distributions."
echo "Default: 1 million passengers (can be customized with --total-records)"
echo "This may take several minutes depending on the number of records."
echo

if wait_for_confirmation; then
    # Ask user for passenger count
    echo "Choose passenger population size:"
    echo "  1) Small - 100,000 passengers (fast, good for testing)"
    echo "  2) Medium - 1,000,000 passengers (recommended for workshops)"
    echo "  3) Large - 10,000,000 passengers (full dataset, takes longer)"
    echo "  4) Custom - Enter your own number"
    echo
    read -p "Enter your choice (1-4, default: 2): " -n 1 -r
    echo

    case $REPLY in
        1)
            passenger_count=100000
            print_status "Using small dataset (100K passengers)..."
            ;;
        3)
            passenger_count=10000000
            print_status "Using large dataset (10M passengers)..."
            ;;
        4)
            echo
            read -p "Enter number of passengers: " passenger_count
            if ! [[ "$passenger_count" =~ ^[0-9]+$ ]] || [ "$passenger_count" -le 0 ]; then
                print_warning "Invalid number, using default (1M passengers)"
                passenger_count=1000000
            fi
            print_status "Using custom dataset ($passenger_count passengers)..."
            ;;
        *)
            passenger_count=1000000
            print_status "Using medium dataset (1M passengers)..."
            ;;
    esac

    uv run python scripts/populate_passengers.py --total-records $passenger_count --batch-size 50000 --clear
    if [ $? -ne 0 ]; then
        print_error "Passenger population failed"
        exit 1
    fi
    print_success "Passenger data populated successfully"
fi

# Step 12: Populate Flight Bookings
print_header "Step 12: Populating Flight Bookings"
print_status "Generating realistic flight bookings with high occupancy rates..."
echo "This step creates passenger bookings for flights with aggressive occupancy patterns."
echo "Target: 90-100% occupancy on all flights for maximum passengers per flight"
echo "Allows passenger duplicates across flights (frequent flyers)"
echo "This may take several minutes depending on the number of flights."
echo

if wait_for_confirmation; then
    print_status "Using aggressive booking population for high passenger counts..."
    
    # Use the aggressive booking script for high occupancy rates
    uv run python scripts/populate_bookings_aggressive.py --clear --batch-size 15000

    if [ $? -ne 0 ]; then
        print_error "Flight booking population failed"
        exit 1
    fi
    print_success "Flight bookings populated successfully"
fi

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
echo "  ✓ Aircraft fleets (realistic fleets optimized for airline operations)"
echo "  ✓ Flight schedules (2025 & first half 2026, max 1000 flights/day)"
echo "  ✓ Passenger data (up to 1 million passengers with global distribution)"
echo "  ✓ Flight bookings (max 100 bookings per passenger, optimized occupancy rates)"

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
echo "  • Validate constraints: uv run python scripts/validate_workshop_constraints.py"
echo "  • Run validation: uv run python scripts/validate_models.py"
echo "  • View statistics: uv run python scripts/airlines_stats.py"
echo "  • View aircraft stats: uv run python scripts/planes_stats.py"
echo "  • View route stats: uv run python scripts/routes_stats.py"
echo "  • Debug aircraft capacity: uv run python scripts/debug_aircraft_capacity.py"
echo "  • Validate passenger data: uv run python scripts/validate_passenger_data.py"
echo "  • Validate booking system: uv run python scripts/validate_booking_system.py"
echo "  • Try examples: uv run python scripts/database_example.py"
echo "  • Try route examples: uv run python scripts/route_example.py"
echo "  • Test flight population: uv run python scripts/test_flight_population.py"
echo "  • Test booking population: uv run python scripts/test_optimized_bookings.py"
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