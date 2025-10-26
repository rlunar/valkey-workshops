# Flughafen DB - Airport Database

A modern Python aviation database with SQLModel ORM, featuring normalized airport and country data from OpenFlights.org.

## Quick Start

### 1. Install Dependencies
```bash
uv sync
```

### 2. Setup Database
Choose your database and run the setup script:

**MySQL:**
```bash
mysql -u root -p < docs/mysql_database.sql
```

**MariaDB:**
```bash
mariadb -u root -p < docs/mariadb_database.sql
```

**PostgreSQL:**
```bash
sudo -u postgres psql < docs/postgresql_database.sql
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 4. Complete Setup (Recommended)
```bash
# Run the complete setup script (imports all data)
bash scripts/setup_workshop.sh
```

This imports all available data: countries, airports, airlines, aircraft types, and routes.

**Or setup step by step:**
```bash
# Reset database (creates fresh tables)
uv run python scripts/reset_database.py

# Import countries data from OpenFlights.org
uv run python scripts/download_countries.py
```

That's it! Your database now has ~260 countries with ISO codes and is ready for use.

## What You Get

After running the basic setup, your database will contain:
- **Country Table**: ~260 countries with ISO 2-letter codes (US, DE, JP), ISO 3-letter codes (USA, DEU, JPN), and DAFIF aviation codes
- **Normalized Schema**: Clean separation between operational and geographic data
- **Ready for Expansion**: Add airports, airlines, flights, and passenger data as needed

After importing all data (using `setup_workshop.sh`), you'll also have:
- **Airport Table**: ~7,700 airports with ICAO/IATA codes and operational data
- **AirportGeo Table**: Geographic data with coordinates, altitude, timezone, and country references
- **Airline Table**: ~6,100+ airlines with IATA/ICAO codes and operational details
- **AirplaneType Table**: ~246 aircraft types with IATA/ICAO codes from OpenFlights
- **Route Table**: ~67,600+ routes between airports operated by airlines with equipment details
- **Country Integration**: All data properly linked to countries via foreign keys and ISO codes

## Import Additional Data

### Download & Import All Data
```bash
# Complete setup with all data sources
bash scripts/setup_workshop.sh
```

### Individual Data Imports

**Airports:**
```bash
uv run python scripts/download_airports.py
```

**Airlines:**
```bash
uv run python scripts/download_airlines.py
```

**Aircraft Types:**
```bash
uv run python scripts/download_planes.py
```

**Routes:**
```bash
uv run python scripts/download_routes.py
```

### Airport Data Import

This script downloads and imports ~7,700 airports worldwide from OpenFlights.org with:
- **Core Airport Data**: ICAO/IATA codes, names, types
- **Geographic Data**: Coordinates, altitude, timezone information
- **Country Matching**: Intelligent matching of airport countries to your country database using ISO codes

### Airlines Data Import

The airlines import provides:
- **Airline Information**: Names, IATA/ICAO codes, callsigns
- **Operational Status**: Active/inactive status tracking
- **Country Data**: Home country information
- **OpenFlights Integration**: Maintains OpenFlights ID references

### Aircraft Types Data Import

The aircraft types import provides:
- **Aircraft Models**: Complete aircraft type names (e.g., "Boeing 737-800")
- **IATA Codes**: 3-letter aircraft codes (e.g., "738")
- **ICAO Codes**: 4-letter aircraft codes (e.g., "B738")
- **Manufacturer Coverage**: Boeing, Airbus, Embraer, and many others

### Routes Data Import

The routes import provides:
- **Route Information**: ~67,600+ routes between airports worldwide
- **Airline Operations**: Routes operated by specific airlines with IATA/ICAO codes
- **Airport Connections**: Source and destination airports with IATA/ICAO codes
- **Flight Details**: Codeshare status, number of stops, and aircraft equipment used
- **OpenFlights Integration**: Maintains OpenFlights ID references for airlines and airports

### What the Airport Import Does

1. **Downloads** fresh airport data from OpenFlights.org
2. **Validates** data quality (coordinates, codes, etc.)
3. **Matches Countries** using multiple strategies:
   - Exact country name matching
   - ISO A2/A3 code detection and conversion
   - Common name variations (e.g., "USA" → "United States")
   - Fuzzy matching for slight differences
4. **Creates Records** in normalized schema:
   - `Airport` table: Core operational data
   - `AirportGeo` table: Geographic data with country foreign keys

### Airport Data Features

- **Normalized Schema**: Separates operational from geographic data
- **Country Integration**: Each airport linked to country via foreign key
- **ISO Code Support**: Automatic ISO A3 code assignment from country data
- **Data Preservation**: Stores original country names alongside normalized references
- **Quality Validation**: Filters invalid coordinates, codes, and data

## Statistics and Validation

View data statistics:
```bash
# View airport statistics
uv run python scripts/airports_stats.py

# View airline statistics  
uv run python scripts/airlines_stats.py

# View aircraft type statistics
uv run python scripts/planes_stats.py

# View route statistics
uv run python scripts/routes_stats.py

# Validate all models
uv run python scripts/validate_models.py
```

## Usage Example

```python
from models.database import DatabaseManager
from models import Country
from sqlmodel import Session, select

db_manager = DatabaseManager()

with Session(db_manager.engine) as session:
    # Find a country by ISO code
    country = session.exec(
        select(Country).where(Country.iso_code == "US")
    ).first()
    
    print(f"{country.name}: {country.iso_code} / {country.iso_a3}")
    # Output: United States: US / USA
```

### Example Usage

```python
from models.database import DatabaseManager
from models import Airport, AirportGeo, Country, Airline, AirplaneType, Route
from sqlmodel import Session, select

db_manager = DatabaseManager()

with Session(db_manager.engine) as session:
    # Find airports in a specific country
    us_airports = session.exec(
        select(Airport, AirportGeo, Country)
        .join(AirportGeo)
        .join(Country)
        .where(Country.iso_a3 == "USA")
        .limit(5)
    ).all()
    
    for airport, geo, country in us_airports:
        print(f"{airport.icao} - {airport.name}")
        print(f"  Location: {geo.city}, {country.name}")
        print(f"  Coordinates: {geo.latitude}, {geo.longitude}")
    
    # Find routes from JFK airport
    jfk_routes = session.exec(
        select(Route)
        .where(Route.source_airport_code == "JFK")
        .limit(5)
    ).all()
    
    for route in jfk_routes:
        codeshare = " (Codeshare)" if route.codeshare else ""
        equipment = f" [{route.equipment}]" if route.equipment else ""
        print(f"{route.airline_code}: JFK → {route.destination_airport_code}{codeshare}{equipment}")
    
    # Find Boeing aircraft types
    boeing_aircraft = session.exec(
        select(AirplaneType)
        .where(AirplaneType.name.contains("Boeing"))
        .limit(5)
    ).all()
    
    for aircraft in boeing_aircraft:
        print(f"{aircraft.iata}/{aircraft.icao} - {aircraft.name}")
```

## Sample SQL Queries

Here are sample SQL queries to validate different query patterns and explore the database:

### Basic Data Validation

```sql
-- Check data counts
SELECT 'Countries' as table_name, COUNT(*) as count FROM country
UNION ALL
SELECT 'Cities', COUNT(*) FROM city
UNION ALL
SELECT 'Airports', COUNT(*) FROM airport
UNION ALL
SELECT 'Airlines', COUNT(*) FROM airline
UNION ALL
SELECT 'Aircraft Types', COUNT(*) FROM airplane_type
UNION ALL
SELECT 'Routes', COUNT(*) FROM route
UNION ALL
SELECT 'City-Airport Relations', COUNT(*) FROM city_airport_relation;

-- Verify data integrity
SELECT 
    COUNT(*) as total_airports,
    COUNT(CASE WHEN iata IS NOT NULL THEN 1 END) as with_iata,
    COUNT(CASE WHEN icao IS NOT NULL THEN 1 END) as with_icao
FROM airport;
```

### Geographic Queries

```sql
-- Find airports near a specific location (within 100km of coordinates)
SELECT 
    a.icao, a.iata, a.name,
    ag.city, ag.country,
    ag.latitude, ag.longitude,
    ROUND(
        6371 * acos(
            cos(radians(40.7128)) * cos(radians(ag.latitude)) * 
            cos(radians(ag.longitude) - radians(-74.0060)) + 
            sin(radians(40.7128)) * sin(radians(ag.latitude))
        ), 2
    ) AS distance_km
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE ag.latitude IS NOT NULL AND ag.longitude IS NOT NULL
HAVING distance_km <= 100
ORDER BY distance_km
LIMIT 10;

-- Find cities with the most airports nearby
SELECT 
    c.name as city_name,
    c.country_code,
    c.population,
    COUNT(car.airport_id) as nearby_airports,
    AVG(car.distance_km) as avg_distance_km,
    MAX(car.accessibility_score) as best_accessibility
FROM city c
JOIN city_airport_relation car ON c.city_id = car.city_id
GROUP BY c.city_id, c.name, c.country_code, c.population
HAVING nearby_airports >= 2
ORDER BY nearby_airports DESC, c.population DESC
LIMIT 15;
```

### Flight Planning Queries

```sql
-- Find primary airports for major cities
SELECT 
    c.name as city_name,
    c.country_code,
    c.population,
    a.icao, a.iata, a.name as airport_name,
    car.distance_km,
    car.accessibility_score,
    c.flight_demand_score,
    c.recommended_daily_flights
FROM city c
JOIN city_airport_relation car ON c.city_id = car.city_id
JOIN airport a ON car.airport_id = a.airport_id
WHERE car.is_primary_airport = 1
    AND c.population > 1000000
ORDER BY c.population DESC
LIMIT 20;

-- Analyze flight demand by country
SELECT 
    co.name as country_name,
    co.iso_code,
    COUNT(DISTINCT c.city_id) as cities_count,
    AVG(c.population) as avg_city_population,
    AVG(c.flight_demand_score) as avg_demand_score,
    SUM(c.recommended_daily_flights) as total_recommended_flights
FROM country co
JOIN city c ON co.iso_code = c.country_code
WHERE c.population IS NOT NULL
GROUP BY co.country_id, co.name, co.iso_code
HAVING cities_count >= 5
ORDER BY total_recommended_flights DESC
LIMIT 15;
```

### Route Analysis

```sql
-- Find busiest routes (most airlines operating)
SELECT 
    r.source_airport_code,
    r.destination_airport_code,
    COUNT(DISTINCT r.airline_code) as airlines_count,
    COUNT(*) as total_routes,
    GROUP_CONCAT(DISTINCT r.airline_code ORDER BY r.airline_code) as airlines
FROM route r
GROUP BY r.source_airport_code, r.destination_airport_code
HAVING airlines_count >= 3
ORDER BY airlines_count DESC, total_routes DESC
LIMIT 20;

-- Airport connectivity analysis
SELECT 
    a.icao, a.iata, a.name,
    ag.city, ag.country,
    COUNT(DISTINCT r.destination_airport_code) as destinations,
    COUNT(DISTINCT r.airline_code) as airlines,
    COUNT(*) as total_routes
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
LEFT JOIN route r ON a.iata = r.source_airport_code OR a.icao = r.source_airport_code
WHERE a.iata IS NOT NULL
GROUP BY a.airport_id, a.icao, a.iata, a.name, ag.city, ag.country
HAVING total_routes > 0
ORDER BY destinations DESC, total_routes DESC
LIMIT 25;
```

### Aircraft and Airline Analysis

```sql
-- Most popular aircraft types on routes
SELECT 
    at.name as aircraft_name,
    at.iata as aircraft_code,
    COUNT(*) as routes_count,
    COUNT(DISTINCT r.airline_code) as airlines_using,
    COUNT(DISTINCT r.source_airport_code) as airports_served
FROM route r
JOIN airplane_type at ON r.equipment = at.iata
GROUP BY at.airplane_type_id, at.name, at.iata
ORDER BY routes_count DESC
LIMIT 15;

-- Airline fleet diversity
SELECT 
    al.name as airline_name,
    al.iata as airline_code,
    al.country,
    COUNT(DISTINCT r.equipment) as aircraft_types,
    COUNT(DISTINCT r.source_airport_code) as airports_served,
    COUNT(*) as total_routes
FROM airline al
JOIN route r ON al.iata = r.airline_code OR al.icao = r.airline_code
WHERE r.equipment IS NOT NULL AND r.equipment != ''
GROUP BY al.airline_id, al.name, al.iata, al.country
HAVING aircraft_types >= 5
ORDER BY aircraft_types DESC, total_routes DESC
LIMIT 20;
```

### Data Quality Checks

```sql
-- Check for orphaned records
SELECT 'Airports without geo data' as issue, COUNT(*) as count
FROM airport a
LEFT JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE ag.airport_id IS NULL

UNION ALL

SELECT 'Routes with invalid source airports', COUNT(*)
FROM route r
LEFT JOIN airport a ON r.source_airport_code IN (a.iata, a.icao)
WHERE a.airport_id IS NULL

UNION ALL

SELECT 'Routes with invalid destination airports', COUNT(*)
FROM route r
LEFT JOIN airport a ON r.destination_airport_code IN (a.iata, a.icao)
WHERE a.airport_id IS NULL

UNION ALL

SELECT 'City-airport relations without cities', COUNT(*)
FROM city_airport_relation car
LEFT JOIN city c ON car.city_id = c.city_id
WHERE c.city_id IS NULL;

-- Validate coordinate ranges
SELECT 
    'Invalid coordinates' as issue,
    COUNT(*) as count
FROM airport_geo
WHERE latitude < -90 OR latitude > 90 
   OR longitude < -180 OR longitude > 180;
```

### Performance Optimization Queries

```sql
-- Index usage analysis (MySQL)
SHOW INDEX FROM airport;
SHOW INDEX FROM city_airport_relation;

-- Query performance for common patterns
EXPLAIN SELECT a.*, ag.* 
FROM airport a 
JOIN airport_geo ag ON a.airport_id = ag.airport_id 
WHERE ag.iso_a2 = 'US' 
ORDER BY a.name;

-- Check for missing indexes on foreign key relationships
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE REFERENCED_TABLE_SCHEMA = DATABASE()
    AND REFERENCED_TABLE_NAME IS NOT NULL;
```

## Data Sources

- **Countries**: OpenFlights.org country data with ISO 3166-1 codes
- **Cities**: GeoNames.org city data with population information for flight planning
- **Airports**: OpenFlights.org airport database (~7,700 airports worldwide)
- **Airlines**: OpenFlights.org airline database (~6,100+ airlines)
- **Aircraft Types**: OpenFlights.org planes database (~246 aircraft types)
- **Routes**: OpenFlights.org routes database (~67,600+ routes between airports)
- **ISO Codes**: Complete ISO 3166-1 alpha-2 and alpha-3 country code mappings

## Project Structure

```
├── models/           # SQLModel classes (Airport, AirportGeo, Country, Airline, AirplaneType, Route)
├── scripts/          # Database setup and import scripts
│   ├── setup_workshop.sh      # Complete setup script (all data)
│   ├── reset_database.py      # Create fresh database tables
│   ├── download_countries.py  # Import country data
│   ├── download_airports.py   # Import airport data with country matching
│   ├── download_airlines.py   # Import airline data
│   ├── download_planes.py     # Import aircraft type data
│   ├── download_routes.py     # Import route data
│   ├── *_stats.py            # Statistics scripts for each data type
│   ├── route_example.py       # Route usage examples
│   └── validate_models.py     # Model validation
├── utils/            # ISO country code mappings and utilities
├── docs/             # Database setup files and documentation
└── .env.example      # Configuration template
```