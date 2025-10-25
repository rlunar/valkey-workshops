# Flughafen DB SQLModel Implementation

This project implements SQLModel classes for the Flughafen DB (Airport Database) schema, providing a modern Python ORM interface for the aviation database.

## Overview

The Flughafen DB is a comprehensive airport database containing information about airports, airlines, flights, passengers, bookings, employees, and weather data. This implementation converts the original MySQL schema into SQLModel classes with support for multiple database backends.

## Features

- **Complete SQLModel Implementation**: All 13 database tables converted to SQLModel classes
- **Multi-Database Support**: MySQL, MariaDB, and PostgreSQL compatibility
- **Environment-Based Configuration**: Secure credential management using python-dotenv
- **Type Safety**: Full Python type hints and validation
- **Foreign Key Relationships**: Proper relational mapping between entities
- **Automated Setup**: Scripts for database initialization and testing

## Database Schema

The implementation includes the following models:

### Core Aviation Data
- **Airport** - Airport information with IATA/ICAO codes and names
- **AirportGeo** - Geographic coordinates and location data for airports
- **AirportReachable** - Reachability analysis data for route planning
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

## Usage Examples

### Basic Database Connection

```python
from models.database import DatabaseManager
from models import Airport, Flight, Passenger

# Uses .env configuration automatically
db_manager = DatabaseManager()

# Create tables
db_manager.create_tables()

# Query data
with Session(db_manager.engine) as session:
    airports = session.exec(select(Airport)).all()
    print(f"Found {len(airports)} airports")
```

### Complex Queries

```python
from sqlmodel import Session, select

# Join queries across multiple tables
with Session(db_manager.engine) as session:
    # Get flights with airline and airport information
    query = (
        select(Flight, Airline, Airport)
        .join(Airline, Flight.airline_id == Airline.airline_id)
        .join(Airport, Flight.from_airport == Airport.airport_id)
        .where(Airport.iata == "VIE")
    )
    
    results = session.exec(query).all()
    for flight, airline, airport in results:
        print(f"{airline.airlinename} flight {flight.flightno} from {airport.name}")
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