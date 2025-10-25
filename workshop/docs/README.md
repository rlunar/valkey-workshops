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

### 4. Reset Database & Import Countries
```bash
# Reset database (creates fresh tables)
uv run python scripts/reset_database.py

# Import countries data from OpenFlights.org
uv run python scripts/download_countries.py
```

That's it! Your database now has ~260 countries with ISO codes and is ready for use.

## What You Get

After running the setup, your database will contain:
- **Country Table**: ~260 countries with ISO 2-letter codes (US, DE, JP), ISO 3-letter codes (USA, DEU, JPN), and DAFIF aviation codes
- **Normalized Schema**: Clean separation between airport operational data and geographic data
- **Ready for Expansion**: Add airports, airlines, flights, and passenger data as needed

## Optional: Import Airports

If you also want airport data:
```bash
uv run python scripts/download_airports.py
```

This adds ~7,700 airports worldwide with full geographic and operational data.

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

## Project Structure

```
├── models/           # SQLModel classes
├── scripts/          # Database setup and import scripts
├── utils/            # ISO country code mappings
├── docs/             # Database setup files
└── .env.example      # Configuration template
```