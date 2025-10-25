# ISO 3166-1 Alpha-3 Implementation

This document describes the implementation of ISO 3166-1 alpha-3 country codes to improve country matching between airport and country data.

## Overview

Added `iso_a3` fields to both `Country` and `AirportGeo` tables to enable better country matching using standardized 3-letter country codes (e.g., "USA", "DEU", "JPN").

## Changes Made

### 1. Model Updates

#### Country Model (`models/country.py`)
- Added `iso_a3: Optional[str] = Field(max_length=3, unique=True, index=True)`
- Field is optional, unique, and indexed for performance

#### AirportGeo Model (`models/airport_geo.py`)
- Added `iso_a3: Optional[str] = Field(default=None, max_length=3, index=True)`
- Field is optional and indexed for lookups

### 2. Utility Functions

#### ISO Country Code Mapping (`utils/iso_country_codes.py`)
- Complete mapping between ISO 2-letter and 3-letter codes
- Utility functions for conversion and validation:
  - `get_iso_a3_from_iso_a2(iso_a2)` - Convert 2-letter to 3-letter code
  - `get_iso_a2_from_iso_a3(iso_a3)` - Convert 3-letter to 2-letter code
  - `validate_iso_a3(iso_a3)` - Validate 3-letter code
  - `validate_iso_a2(iso_a2)` - Validate 2-letter code

### 3. Data Import Updates

#### Country Import (`scripts/download_countries.py`)
- Automatically generates ISO A3 codes from existing ISO A2 codes
- Uses the mapping utility to ensure accuracy

#### Airport Import (`scripts/download_airports.py`)
- Populates `iso_a3` field in AirportGeo records
- Retrieves ISO A3 code from the matched country record

### 4. Validation and Maintenance Scripts

#### Country Matching Validation (`scripts/validate_country_matching.py`)
- Analyzes country matching between airport data and country database
- Identifies missing countries and ISO code coverage gaps
- Provides suggestions for improving data quality

#### ISO A3 Code Updater (`scripts/update_country_iso_a3.py`)
- Updates existing country records with ISO A3 codes
- Interactive script with coverage reporting
- Safe batch updates with verification

### 5. Documentation Updates

#### README.md
- Updated Country table documentation to include `iso_a3` field
- Updated AirportGeo table documentation to include `iso_a3` field
- Enhanced data processing section to mention ISO A3 code generation

#### Test Updates (`tests/test_normalized_import.py`)
- Updated test output to display country_id and iso_a3 instead of deprecated country field
- Maintains test functionality with normalized data structure

## Usage Examples

### Finding Countries by ISO A3 Code
```python
from sqlmodel import Session, select
from models.country import Country

# Find country by ISO A3 code
country = session.exec(
    select(Country).where(Country.iso_a3 == "USA")
).first()
```

### Finding Airports by Country ISO A3 Code
```python
from sqlmodel import Session, select
from models.airport import Airport
from models.airport_geo import AirportGeo

# Find airports in a specific country using ISO A3
airports = session.exec(
    select(Airport)
    .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
    .where(AirportGeo.iso_a3 == "USA")
).all()
```

### Converting Between ISO Codes
```python
from utils.iso_country_codes import get_iso_a3_from_iso_a2, get_iso_a2_from_iso_a3

# Convert US to USA
iso_a3 = get_iso_a3_from_iso_a2("US")  # Returns "USA"

# Convert USA to US
iso_a2 = get_iso_a2_from_iso_a3("USA")  # Returns "US"
```

## Benefits

1. **Improved Data Matching**: ISO A3 codes provide a standardized way to match countries
2. **Better Data Quality**: Validation functions ensure code accuracy
3. **Enhanced Queries**: Multiple ways to query countries (name, ISO A2, ISO A3)
4. **Future-Proof**: Standard ISO codes ensure long-term compatibility
5. **Performance**: Indexed fields enable fast country lookups

## Migration Path

For existing databases:

1. Run database schema migration to add new columns
2. Execute `scripts/update_country_iso_a3.py` to populate existing records
3. Re-import airport data to populate AirportGeo iso_a3 fields
4. Use `scripts/validate_country_matching.py` to verify data quality

## Validation

Use the validation script to check implementation:

```bash
python scripts/validate_country_matching.py
```

This will show:
- Country matching statistics
- ISO A3 code coverage
- Suggestions for improvements
- Data quality metrics