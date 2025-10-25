# Flughafen DB SQLModel Implementation

This project implements SQLModel classes for the Flughafen DB (Airport Database) schema, providing a modern Python ORM interface for the aviation database.

## Overview

The Flughafen DB is a comprehensive airport database containing information about airports, airlines, flights, passengers, bookings, employees, and weather data. This implementation converts the original MySQL schema into SQLModel classes with support for multiple database backends.

## Features

- **Normalized Airport Schema**: Airport data properly separated into operational and geographic tables following database normalization principles
- **Complete SQLModel Implementation**: All database tables converted to SQLModel classes
- **Multi-Database Support**: MySQL, MariaDB, and PostgreSQL compatibility
- **Environment-Based Configuration**: Secure credential management using python-dotenv
- **Type Safety**: Full Python type hints and validation
- **Foreign Key Relationships**: Proper relational mapping between entities
- **Automated Setup**: Scripts for database initialization and testing

## Database Schema

The implementation includes the following models with a **normalized airport schema**:

### Normalized Airport Schema

The airport data has been properly normalized into two related tables following database normalization principles:

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

**Benefits of Normalization:**
- **Separation of Concerns**: Core operational data separated from geographic data
- **Query Optimization**: Can query airports without loading geographic data when not needed
- **Data Integrity**: Geographic data is optional and properly constrained
- **Maintainability**: Changes to geographic data don't affect core airport operations

### Core Aviation Data
- **Airport** - Core airport operational information (IATA/ICAO codes, names, types)
- **AirportGeo** - Geographic data for airports (coordinates, city, country, timezone)
- **Airline** - Airline information with base airport relationships
- **Airplane** & **AirplaneType** - Aircraft fleet and specifications

### Flight Operations
- **Flight** - Individual flight instances with schedules and routes
- **FlightSchedule** - Recurring flight schedules with day-of-week patterns
- **FlightLog** - Audit trail for flight modifications and changes

### Passenger Management
- **Passenger** - Basic passenger identification and passport information
- **PassengerDetails** - Extended passenger information (address, contact)
- **Booking** - Flight reservations linking passengers to specific flights

### Operations Support
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

6. **Import real airport data (optional):**
   ```bash
   # Download and import airports data (interactive)
   uv run python scripts/download_airports.py
   
   # View statistics about the imported data
   uv run python scripts/airports_stats.py
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

## Airport Data Import

The project includes a script to download and import real airport data from OpenFlights.org into the normalized schema:

### Download and Import Airports

```bash
uv run python scripts/reset_database.py  

# Download and import airports data (interactive)
uv run python scripts/download_airports.py

# View statistics about the imported data
uv run python scripts/airports_stats.py
```

This will:
1. Download the latest airports.dat from OpenFlights.org (~7,700+ airports)
2. Analyze the data structure using Polars
3. Filter for valid airports with ICAO codes (required by our schema)
4. Insert new airports into both `airport` and `airport_geo` tables (skips existing ones)
5. Maintain referential integrity between the normalized tables

**Data Processing:**
- Imports all 14 fields from OpenFlights data and splits them between Airport and AirportGeo tables
- **Airport table**: Receives core operational data (IATA/ICAO codes, name, type, data source)
- **AirportGeo table**: Receives geographic data (coordinates, altitude, timezone information, city, country)
- Filters for commercial airports only (excludes heliports, seaplane bases)
- Requires valid ICAO codes (4-character international codes)
- Validates IATA codes (3-character codes, optional)
- Handles international airport names (200-character limit)
- Processes geographic coordinates with high precision (8 decimal places)
- Includes altitude data (feet above sea level)
- Timezone information (UTC offset, DST rules, Olson timezone names)
- Airport type classification and data source tracking
- Processes ~7,700 airports from 237 countries

### Airport Data Source

The airport data comes from [OpenFlights.org](https://openflights.org/data), which provides:
- Airport names, IATA/ICAO codes
- Geographic coordinates
- City and country information
- Airport types (airports, heliports, etc.)

The import script filters for commercial airports with valid ICAO codes and automatically splits the data between the Airport and AirportGeo tables to maintain the normalized schema.

### Import Options

**Main Import Script:**
- `download_airports.py` - Downloads data and imports into database (interactive)
- Automatically handles missing data files
- Inserts new airports only (safe for existing databases)
- Option to show database statistics without importing

**Additional Tools:**
- `airports_stats.py` - Detailed statistics about downloaded data
- `reset_database.py` - Reset database schema (drops all tables and recreates with new schema)

**Schema Management:**
If you have an existing database with the old Airport schema (4 fields), you'll need to reset it to use the enhanced schema (15 fields):
```bash
uv run python scripts/reset_database.py  # ⚠️ Drops all existing data
uv run python scripts/download_airports.py  # Import fresh airport data
```

## Usage Examples

### Working with Normalized Airport Data

```python
from models.database import DatabaseManager
from models import Airport, AirportGeo, Flight, Passenger
from sqlmodel import Session, select

# Uses .env configuration automatically
db_manager = DatabaseManager()

# Create tables
db_manager.create_tables()

# Query airport with geographic data
with Session(db_manager.engine) as session:
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
```

### Geographic Queries

```python
from sqlmodel import Session, select

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

# Complex flight queries with full airport information
with Session(db_manager.engine) as session:
    # Get flights with airline and complete airport information
    query = (
        select(Flight, Airline, Airport, AirportGeo)
        .join(Airline, Flight.airline_id == Airline.airline_id)
        .join(Airport, Flight.from_airport == Airport.airport_id)
        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
        .where(AirportGeo.country == "Austria")
    )
    
    results = session.exec(query).all()
    for flight, airline, airport, geo in results:
        print(f"{airline.airlinename} flight {flight.flightno} from {airport.name} in {geo.city}")
```

### Data Relationships

```python
# Booking with passenger and flight details
booking_query = (
    select(Booking, Passenger, Flight)
    .join(Passenger, Booking.passenger_id == Passenger.passenger_id)
    .join(Flight, Booking.flight_id == Flight.flight_id)
    .limit(10)
)

results = session.exec(booking_query).all()
for booking, passenger, flight in results:
    print(f"{passenger.firstname} {passenger.lastname} "
          f"on flight {flight.flightno} - Seat: {booking.seat}")
```

## Project Structure

```
├── docs/
│   ├── flughafendb_schema_en.sql    # Original database schema
│   └── README.md                    # This documentation
├── models/
│   ├── __init__.py                  # Model exports
│   ├── database.py                  # Database connection management
│   ├── airport.py                   # Airport-related models
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
│   ├── airports_stats.py            # View airport data statistics
│   ├── reset_database.py            # Reset database schema
│   └── validate_models.py           # Model validation
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore rules
└── pyproject.toml                   # Project dependencies
```

## Key Implementation Details

### Type Safety and Validation
- All models use proper Python type hints
- SQLModel provides runtime validation
- Decimal fields for precise financial/coordinate data
- Enum classes for categorical data (departments, weather conditions)

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
```

**PostgreSQL with pgcli:**
```bash
pgcli -U flughafen_user -d flughafendb
\dt
\d airport
```

**Standard CLI tools:**
```bash
# MySQL/MariaDB
mysql -u flughafen_user -p flughafendb -e "SHOW TABLES;"

# PostgreSQL
psql -U flughafen_user -d flughafendb -c "\dt"
```

## Original Schema License

The Flughafen DB by Stefan Proell, Eva Zangerle, Wolfgang Gassler is licensed under CC BY 4.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/4.0

## Dependencies

- **sqlmodel**: Modern Python SQL toolkit and ORM
- **python-dotenv**: Environment variable management
- **pymysql**: MySQL/MariaDB database driver
- **psycopg2-binary**: PostgreSQL database driver

## Troubleshooting

### Database Setup Issues

**MySQL/MariaDB Connection Problems:**
```bash
# Check if MySQL/MariaDB is running
sudo systemctl status mysql
# or
sudo systemctl status mariadb

# Test connection
mysql -u flughafen_user -p -e "SELECT 1;"

# Check user privileges
mysql -u root -p -e "SHOW GRANTS FOR 'flughafen_user'@'localhost';"
```

**PostgreSQL Connection Problems:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U flughafen_user -d flughafendb -c "SELECT 1;"

# Check user privileges
sudo -u postgres psql -c "\du flughafen_user"
```

**Common Database Errors:**

1. **"Access denied" errors**: 
   - Verify username/password in `.env`
   - Check user privileges with `SHOW GRANTS` (MySQL) or `\du` (PostgreSQL)

2. **"Database does not exist"**:
   - Ensure you created the database: `CREATE DATABASE flughafendb;`

3. **"Connection refused"**:
   - Check if database server is running
   - Verify host and port in `.env` file

4. **Character encoding issues (MySQL/MariaDB)**:
   - Ensure database uses `utf8mb4` charset: 
   ```sql
   ALTER DATABASE flughafendb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

### Application Issues

1. **Import Errors**: Run `uv sync` to install all dependencies
2. **Database Connection**: Verify credentials in `.env` file
3. **Table Creation**: Ensure database exists and user has CREATE privileges
4. **Type Errors**: Check that all required fields are provided when creating records

### Database-Specific Notes

- **MySQL/MariaDB**: Uses `pymysql` driver for pure Python compatibility
- **PostgreSQL**: Requires `psycopg2-binary` for optimal performance
- **Port Defaults**: MySQL/MariaDB (3306), PostgreSQL (5432)
- **Character Sets**: UTF-8 encoding recommended for international airport names

### Quick Database Reset

If you need to start over:

**MySQL:**
```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS flughafendb; DROP USER IF EXISTS 'flughafen_user'@'localhost';"
mysql -u root -p < docs/mysql_database.sql
```

**MariaDB:**
```bash
mariadb -u root -p -e "DROP DATABASE IF EXISTS flughafendb; DROP USER IF EXISTS 'flughafen_user'@'localhost';"
mariadb -u root -p < docs/mariadb_database.sql
```

**PostgreSQL:**
```bash
sudo -u postgres psql -c "DROP DATABASE IF EXISTS flughafendb; DROP USER IF EXISTS flughafen_user;"
sudo -u postgres psql < docs/postgresql_database.sql
```

## Contributing

When extending the models:
1. Maintain type safety with proper annotations
2. Add appropriate field constraints (max_length, unique, etc.)
3. Update foreign key relationships as needed
4. Test with all supported database backends