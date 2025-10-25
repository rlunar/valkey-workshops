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
from models import Airport, Airline, Flight, Passenger, Booking
from models.database import DatabaseManager

# Database connection uses .env configuration automatically
db_manager = DatabaseManager()

# Use the models
with Session(db_manager.engine) as session:
    airports = session.exec(select(Airport)).all()
```

## Available Models

- **Airport** - Airport information (IATA/ICAO codes, names)
- **AirportGeo** - Geographic data for airports
- **Airline** - Airline information with base airports
- **Airplane** & **AirplaneType** - Aircraft and aircraft types
- **Flight** & **FlightSchedule** - Flight data and schedules
- **Passenger** & **PassengerDetails** - Passenger information
- **Booking** - Flight bookings
- **Employee** - Employee data
- **WeatherData** - Weather station data

## Example

Run the example script:

```bash
uv run python scripts/database_example.py
```

## License

The Flughafen DB by Stefan Proell, Eva Zangerle, Wolfgang Gassler is licensed under CC BY 4.0.