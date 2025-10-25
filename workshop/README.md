# Flughafen DB SQLModel Implementation

This project implements SQLModel classes for the Flughafen DB (Airport Database) schema, providing a modern Python ORM interface for the aviation database with a **normalized airport schema**.

## Overview

The Flughafen DB is a comprehensive airport database containing information about airports, airlines, flights, passengers, bookings, employees, and weather data. This implementation converts the original MySQL schema into SQLModel classes with support for multiple database backends.

**Key Feature**: The airport data has been normalized into two separate tables following database normalization principles:
- **Airport**: Core operational data (codes, names, types)
- **AirportGeo**: Geographic and location-specific data (coordinates, timezone, altitude)

## Features

- **Normalized Airport Schema**: Airport data properly separated into operational and geographic tables
- **Complete SQLModel Implementation**: All database tables converted to SQLModel classes
- **Multi-Database Support**: MySQL, MariaDB, and PostgreSQL compatibility
- **Environment-Based Configuration**: Secure credential management using python-dotenv
- **Type Safety**: Full Python type hints and validation
- **Foreign Key Relationships**: Proper relational mapping between entities
- **Automated Setup**: Scripts for database initialization and testing

## Database Schema

### Normalized Airport Schema

The airport data has been normalized into two related tables:

```
┌─────────────────┐    1:1    ┌──────────────────┐
│     Airport     │◄─────────►│   AirportGeo     │
├─────────────────┤           ├──────────────────┤
│ airport_id (PK) │           │ airport_id (PK,FK)│
│ iata            │           │ city             │
│ icao (UNIQUE)   │           │ country          │
│ name            │           │ latitude         │
│ airport_type    │           │ longitude        │
│ data_source     │           │ altitude         │
│ openflights_id  │           │ timezone_offset  │
└─────────────────┘           │ dst              │
                              │ timezone_name    │
                              └──────────────────┘
```

**Airport Table (Core Operational Data):**
- `airport_id`: Primary key (auto-increment)
- `iata`: 3-character IATA code (optional, indexed)
- `icao`: 4-character ICAO code (required, unique)
- `name`: Airport name (required, indexed, max 200 chars)
- `airport_type`: Enum (airport, heliport, etc.)
- `data_source`: Source of the data (e.g., "OpenFlights")
- `openflights_id`: Original OpenFlights ID for reference

**AirportGeo Table (Geographic Data):**
- `airport_id`: Primary key and foreign key to Airport
- `city`: City name (optional, max 100 chars)
- `country`: Country name (optional, max 100 chars)
- `latitude`: Decimal coordinates (11 digits, 8 decimal places)
- `longitude`: Decimal coordinates (11 digits, 8 decimal places)
- `altitude`: Altitude in feet (integer, optional)
- `timezone_offset`: Hours from UTC (decimal, 4.2 precision)
- `dst`: Daylight saving time type (enum)
- `timezone_name`: Olson timezone name (max 50 chars)

### Complete Schema Overview

The implementation includes the following models:

#### Core Aviation Data
- **Airport** - Core airport operational information (IATA/ICAO codes, names, types)
- **AirportGeo** - Geographic data for airports (coordinates, city, country, timezone)
- **Country** - Country information with ISO and DAFIF codes for airport lookups
- **Airline** - Airline information with base airport relationships
- **Airplane** & **AirplaneType** - Aircraft fleet and specifications

#### Flight Operations
- **Flight** - Individual flight instances with schedules and routes
- **FlightSchedule** - Recurring flight schedules with day-of-week patterns
- **FlightLog** - Audit trail for flight modifications and changes

#### Passenger Management
- **Passenger** - Basic passenger identification and passport information
- **PassengerDetails** - Extended passenger information (address, contact)
- **Booking** - Flight reservations linking passengers to specific flights

#### Operations Support
- **Employee** - Staff information with department assignments and credentials
- **WeatherData** - Weather station data for operational planning

## Installation

### Prerequisites
- Python 3.12+
- uv package manager
- Database server (MySQL, MariaDB, or PostgreSQL)
- Optional: mycli, pgcli for enhanced database interaction

### Database Setup

Choose one of the following database systems and follow the setup instructions:

> **Note**: Before running the setup commands, edit the corresponding SQL file in `docs/` to change `'your_secure_password'` to your actual password.

#### MySQL Setup

**Single command setup:**
```bash
mysql -u root -p < docs/mysql_database.sql
```

**Or using mycli:**
```bash
mycli -u root -p < docs/mysql_database.sql
```

#### MariaDB Setup

**Single command setup:**
```bash
mariadb -u root -p < docs/mariadb_database.sql
```

**Or using mycli:**
```bash
mycli -u root -p < docs/mariadb_database.sql
```

#### PostgreSQL Setup

**Single command setup:**
```bash
sudo -u postgres psql < docs/postgresql_database.sql
```

**Or using pgcli:**
```bash
sudo -u postgres pgcli < docs/postgresql_database.sql
```

### Project Setup

1. **Install Python dependencies:**
   ```bash
   uv sync
   ```

2. **Configure database connection:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your database credentials:**
   ```env
   # For MySQL/MariaDB
   DB_TYPE=mysql
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=flughafendb
   DB_USER=flughafen_user
   DB_PASSWORD=your_secure_password

   # For PostgreSQL
   DB_TYPE=postgresql
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=flughafendb
   DB_USER=flughafen_user
   DB_PASSWORD=your_secure_password
   ```

4. **Create database tables:**
   ```bash
   uv run python scripts/setup_database.py
   ```

5. **Verify setup:**
   ```bash
   uv run python scripts/database_example.py
   ```

6. **Import real data (optional):**
   ```bash
   # Download and import airports data (interactive)
   uv run python scripts/download_airports.py
   
   # Download and import countries data (interactive)
   uv run python scripts/download_countries.py
   
   # View statistics about the imported data
   uv run python scripts/airports_stats.py
   uv run python scripts/countries_stats.py
   ```

## Migration from Single Airport Table

If you have an existing database with the old single Airport table schema, you'll need to migrate to the normalized schema:

### Migration Process

1. **Backup your existing data:**
   ```bash
   # MySQL/MariaDB
   mysqldump -u flughafen_user -p flughafendb > backup.sql
   
   # PostgreSQL
   pg_dump -U flughafen_user flughafendb > backup.sql
   ```

2. **Run the migration script:**
   ```bash
   # This will create a migration utility to split existing Airport records
   uv run python scripts/migrate_airport_schema.py
   ```

3. **Verify the migration:**
   ```bash
   uv run python scripts/validate_models.py
   ```

### Migration Details

The migration process will:
- Create the new `airport_geo` table
- Move geographic fields from `airport` to `airport_geo`
- Maintain referential integrity via foreign key relationships
- Preserve all existing `airport_id` values
- Handle cases where geographic data might be missing
- Provide rollback capabilities in case of errors

**Fields moved from Airport to AirportGeo:**
- `city` → `airport_geo.city`
- `country` → `airport_geo.country`
- `latitude` → `airport_geo.latitude`
- `longitude` → `airport_geo.longitude`
- `altitude` → `airport_geo.altitude`
- `timezone_offset` → `airport_geo.timezone_offset`
- `dst` → `airport_geo.dst`
- `timezone_name` → `airport_geo.timezone_name`

## Usage Examples

### Working with Normalized Airport Data

```python
from models.database import DatabaseManager
from models import Airport, AirportGeo
from sqlmodel import Session, select

# Uses .env configuration automatically
db_manager = DatabaseManager()

# Create tables
db_manager.create_tables()

with Session(db_manager.engine) as session:
    # Query airport with geographic data
    query = (
        select(Airport, AirportGeo)
        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
        .where(Airport.icao == "LOWW")  # Vienna International Airport
    )
    
    result = session.exec(query).first()
    if result:
        airport, geo = result
        print(f"Airport: {airport.name} ({airport.iata}/{airport.icao})")
        print(f"Location: {geo.city}, {geo.country}")
        print(f"Coordinates: {geo.latitude}, {geo.longitude}")
        print(f"Altitude: {geo.altitude} ft")
```

### Geographic Queries

```python
# Find airports in a specific country
def get_airports_in_country(session: Session, country: str):
    query = (
        select(Airport, AirportGeo)
        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
        .where(AirportGeo.country == country)
    )
    return session.exec(query).all()

# Find airports within a coordinate range
def get_airports_in_region(session: Session, min_lat, max_lat, min_lon, max_lon):
    query = (
        select(Airport, AirportGeo)
        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
        .where(
            AirportGeo.latitude.between(min_lat, max_lat),
            AirportGeo.longitude.between(min_lon, max_lon)
        )
    )
    return session.exec(query).all()

# Get airports by timezone
def get_airports_in_timezone(session: Session, timezone_name: str):
    query = (
        select(Airport, AirportGeo)
        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
        .where(AirportGeo.timezone_name == timezone_name)
    )
    return session.exec(query).all()
```

### Creating Airport Records

```python
# Create airport with geographic data
def create_airport_with_location(session: Session, airport_data: dict):
    # Create core airport record
    airport = Airport(
        iata=airport_data.get('iata'),
        icao=airport_data['icao'],
        name=airport_data['name'],
        airport_type=airport_data.get('airport_type', AirportType.AIRPORT),
        data_source=airport_data.get('data_source'),
        openflights_id=airport_data.get('openflights_id')
    )
    
    session.add(airport)
    session.commit()
    session.refresh(airport)  # Get the generated airport_id
    
    # Create geographic data record
    airport_geo = AirportGeo(
        airport_id=airport.airport_id,
        city=airport_data.get('city'),
        country=airport_data.get('country'),
        latitude=airport_data.get('latitude'),
        longitude=airport_data.get('longitude'),
        altitude=airport_data.get('altitude'),
        timezone_offset=airport_data.get('timezone_offset'),
        dst=airport_data.get('dst'),
        timezone_name=airport_data.get('timezone_name')
    )
    
    session.add(airport_geo)
    session.commit()
    
    return airport, airport_geo
```

### Flight Operations with Airport Data

```python
from models import Flight, Airline

# Get flights with full airport information
def get_flights_with_airport_details(session: Session):
    query = (
        select(Flight, Airline, Airport, AirportGeo)
        .join(Airline, Flight.airline_id == Airline.airline_id)
        .join(Airport, Flight.from_airport == Airport.airport_id)
        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
        .limit(10)
    )
    
    results = session.exec(query).all()
    for flight, airline, airport, geo in results:
        print(f"{airline.name} flight {flight.flightno}")
        print(f"From: {airport.name} ({airport.iata}) in {geo.city}, {geo.country}")
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Database type: mysql, mariadb, or postgresql
DB_TYPE=mysql

# Connection details
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flughafendb
DB_USER=your_username
DB_PASSWORD=your_password

# Optional: Full database URL (overrides individual settings)
# DATABASE_URL=mysql+pymysql://user:pass@host:port/db
```

### Supported Database Types

| Database | Driver | Connection String Format |
|----------|--------|-------------------------|
| MySQL | pymysql | `mysql+pymysql://user:pass@host:port/db` |
| MariaDB | pymysql | `mysql+pymysql://user:pass@host:port/db` |
| PostgreSQL | psycopg2 | `postgresql+psycopg2://user:pass@host:port/db` |

## Real Data Import

The project includes scripts to download and import real aviation data from OpenFlights.org:

### Download and Import Airports

```bash
# Download and import airports data (interactive)
uv run python scripts/download_airports.py

# View statistics about the imported data
uv run python scripts/airports_stats.py
```

This will:
1. Download the latest airports.dat from OpenFlights.org (~7,700+ airports)
2. Analyze the data structure using Polars
3. Filter for valid airports with ICAO codes (required by our schema)
4. Insert new airports into both `airport` and `airport_geo` tables
5. Maintain referential integrity between the tables

**Airport Data Processing:**
- Imports all 14 fields from OpenFlights data
- Splits data between Airport (operational) and AirportGeo (geographic) tables
- Filters for commercial airports only (excludes heliports, seaplane bases)
- Requires valid ICAO codes (4-character international codes)
- Validates IATA codes (3-character codes, optional)
- Handles international airport names (200-character limit)
- Processes geographic coordinates with high precision (8 decimal places)
- Includes altitude data (feet above sea level)
- Timezone information (UTC offset, DST rules, Olson timezone names)
- Airport type classification and data source tracking
- Processes ~7,700 airports from 237 countries

### Download and Import Countries

```bash
# Download and import countries data (interactive)
uv run python scripts/download_countries.py

# View statistics about the imported data
uv run python scripts/countries_stats.py
```

This will:
1. Download the latest countries.dat from OpenFlights.org (~260 countries)
2. Analyze country codes and names
3. Import countries with ISO 3166-1 and DAFIF codes
4. Enable country lookups for airport data

**Country Data Processing:**
- Imports country names, ISO codes, and DAFIF codes
- Validates ISO 3166-1 two-letter country codes
- Handles historical DAFIF codes for aviation purposes
- Supports country lookups for airport geographic data
- Processes ~260 countries and territories

## Project Structure

```
├── docs/
│   ├── flughafendb_schema_en.sql    # Original database schema
│   └── README.md                    # Detailed documentation
├── models/
│   ├── __init__.py                  # Model exports
│   ├── database.py                  # Database connection management
│   ├── airport.py                   # Airport core operational model
│   ├── airport_geo.py               # Airport geographic data model
│   ├── country.py                   # Country model with ISO/DAFIF codes
│   ├── airline.py                   # Airline model
│   ├── airplane.py                  # Aircraft models
│   ├── flight.py                    # Flight operation models
│   ├── passenger.py                 # Passenger models
│   ├── booking.py                   # Booking model
│   ├── employee.py                  # Employee model
│   ├── weather.py                   # Weather data model
│   └── README.md                    # Model documentation
├── scripts/
│   ├── database_example.py          # Usage examples and testing
│   ├── setup_database.py            # Database initialization
│   ├── download_airports.py         # Download and import airport data
│   ├── download_countries.py        # Download and import country data
│   ├── airports_stats.py            # View airport data statistics
│   ├── countries_stats.py           # View country data statistics
│   ├── reset_database.py            # Reset database schema
│   ├── migrate_airport_schema.py    # Migration utility for existing databases
│   └── validate_models.py           # Model validation
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore rules
└── pyproject.toml                   # Project dependencies
```

## Key Implementation Details

### Normalized Airport Schema Benefits

1. **Separation of Concerns**: Operational data separated from geographic data
2. **Query Optimization**: Can query airports without loading geographic data when not needed
3. **Data Integrity**: Geographic data is optional and properly constrained
4. **Maintainability**: Changes to geographic data don't affect core airport operations
5. **Performance**: Indexes can be optimized for specific query patterns

### Type Safety and Validation
- All models use proper Python type hints
- SQLModel provides runtime validation
- Decimal fields for precise coordinate data
- Enum classes for categorical data (airport types, DST types)

### Database Compatibility
- Automatic connection string building based on database type
- Proper field mapping for different SQL dialects
- Foreign key constraints maintained across all backends

### Security Considerations
- Environment-based credential management
- .env files excluded from version control
- No hardcoded database credentials in source code

## Testing and Verification

### Test Database Connection

Run the example script to verify your setup:

```bash
uv run python scripts/database_example.py
```

### Validate Model Structure

```bash
uv run python scripts/validate_models.py
```

### Manual Database Testing

You can also test your database connection manually using the CLI tools:

**MySQL/MariaDB with mycli:**
```bash
mycli -u flughafen_user -p flughafendb
SHOW TABLES;
DESCRIBE airport;
DESCRIBE airport_geo;
```

**PostgreSQL with pgcli:**
```bash
pgcli -U flughafen_user -d flughafendb
\dt
\d airport
\d airport_geo
```

## Troubleshooting

### Migration Issues

**Foreign Key Constraint Errors:**
- Ensure all airport records have corresponding airport_geo records
- Check for orphaned records in either table
- Verify foreign key constraints are properly created

**Data Type Mismatches:**
- Verify decimal precision for coordinates (11 digits, 8 decimal places)
- Check timezone_offset precision (4 digits, 2 decimal places)
- Ensure enum values match defined types

### Query Performance

**Slow JOIN Queries:**
- Ensure indexes exist on `airport_id` in both tables
- Consider creating composite indexes for frequently queried combinations
- Use EXPLAIN to analyze query execution plans

**Common Query Patterns:**
```sql
-- Most efficient: Query with specific airport_id
SELECT a.name, g.city, g.country 
FROM airport a 
JOIN airport_geo g ON a.airport_id = g.airport_id 
WHERE a.airport_id = 123;

-- Efficient: Query with indexed fields
SELECT a.name, g.city, g.country 
FROM airport a 
JOIN airport_geo g ON a.airport_id = g.airport_id 
WHERE a.icao = 'LOWW';

-- Consider indexes: Geographic range queries
SELECT a.name, g.latitude, g.longitude 
FROM airport a 
JOIN airport_geo g ON a.airport_id = g.airport_id 
WHERE g.latitude BETWEEN 47.0 AND 49.0 
  AND g.longitude BETWEEN 16.0 AND 18.0;
```

## Original Schema License

The Flughafen DB by Stefan Proell, Eva Zangerle, Wolfgang Gassler is licensed under CC BY 4.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/4.0

## Dependencies

- **sqlmodel**: Modern Python SQL toolkit and ORM
- **python-dotenv**: Environment variable management
- **pymysql**: MySQL/MariaDB database driver
- **psycopg2-binary**: PostgreSQL database driver

## Contributing

When extending the models:
1. Maintain type safety with proper annotations
2. Add appropriate field constraints (max_length, unique, etc.)
3. Update foreign key relationships as needed
4. Consider the normalized schema when adding airport-related fields
5. Test with all supported database backends