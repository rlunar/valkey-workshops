# Flughafen DB SQLModel Classes

SQLModel classes for the Flughafen DB (Airport Database) schema.

## Installation

```bash
uv sync
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your database credentials:
```env
DB_TYPE=mysql          # mysql, mariadb, or postgresql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flughafendb
DB_USER=your_username
DB_PASSWORD=your_password
```

## Database Setup

Create the database tables:
```bash
uv run python scripts/setup_database.py
```

## Usage

```python
from models import Airport, AirportGeo, Airline, Flight, Passenger, Booking
from models.database import DatabaseManager
from sqlmodel import Session, select

# Database connection uses .env configuration automatically
db_manager = DatabaseManager()

# Query airport with geographic data (normalized schema)
with Session(db_manager.engine) as session:
    # Get airport with location data
    query = (
        select(Airport, AirportGeo)
        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
        .where(Airport.icao == "LOWW")
    )
    
    result = session.exec(query).first()
    if result:
        airport, geo = result
        print(f"{airport.name} in {geo.city}, {geo.country}")
    
    # Query just core airport data (when geographic data not needed)
    airports = session.exec(select(Airport)).all()
    print(f"Found {len(airports)} airports")
```

## Available Models (Normalized Airport Schema)

### Airport Models (Normalized)
- **Airport** - Core airport operational information (IATA/ICAO codes, names, types)
- **AirportGeo** - Geographic data for airports (coordinates, city, country, timezone)

### Other Models
- **Airline** - Airline information with base airports
- **Airplane** & **AirplaneType** - Aircraft and aircraft types
- **Flight** & **FlightSchedule** - Flight data and schedules
- **Passenger** & **PassengerDetails** - Passenger information
- **Booking** - Flight bookings
- **Employee** - Employee data
- **WeatherData** - Weather station data

### Airport Schema Relationship

The airport data follows database normalization principles with a one-to-one relationship:

```
Airport (1) ←→ (1) AirportGeo
```

**Airport Table (Core Data):**
- airport_id, iata, icao, name, airport_type, data_source, openflights_id

**AirportGeo Table (Geographic Data):**
- airport_id (FK), city, country, latitude, longitude, altitude, timezone_offset, dst, timezone_name

## Example

Run the example script:

```bash
uv run python scripts/database_example.py
```

## License

The Flughafen DB by Stefan Proell, Eva Zangerle, Wolfgang Gassler is licensed under CC BY 4.0.