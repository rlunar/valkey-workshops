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

This imports all available data: countries, airports, airlines, and aircraft types.

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
from models import Airport, AirportGeo, Country, Airline, AirplaneType
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
    
    # Find Boeing aircraft types
    boeing_aircraft = session.exec(
        select(AirplaneType)
        .where(AirplaneType.name.contains("Boeing"))
        .limit(5)
    ).all()
    
    for aircraft in boeing_aircraft:
        print(f"{aircraft.iata}/{aircraft.icao} - {aircraft.name}")
```

## Data Sources

- **Countries**: OpenFlights.org country data with ISO 3166-1 codes
- **Airports**: OpenFlights.org airport database (~7,700 airports worldwide)
- **Airlines**: OpenFlights.org airline database (~6,100+ airlines)
- **Aircraft Types**: OpenFlights.org planes database (~246 aircraft types)
- **ISO Codes**: Complete ISO 3166-1 alpha-2 and alpha-3 country code mappings

## Project Structure

```
├── models/           # SQLModel classes (Airport, AirportGeo, Country, Airline, AirplaneType)
├── scripts/          # Database setup and import scripts
│   ├── setup_workshop.sh      # Complete setup script (all data)
│   ├── reset_database.py      # Create fresh database tables
│   ├── download_countries.py  # Import country data
│   ├── download_airports.py   # Import airport data with country matching
│   ├── download_airlines.py   # Import airline data
│   ├── download_planes.py     # Import aircraft type data
│   ├── *_stats.py            # Statistics scripts for each data type
│   └── validate_models.py     # Model validation
├── utils/            # ISO country code mappings and utilities
├── docs/             # Database setup files and documentation
└── .env.example      # Configuration template
```