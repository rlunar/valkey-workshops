# Flight Population Scripts

This directory contains scripts to populate realistic flight schedules based on the flight rules defined in `docs/flight_rules.md`.

## Overview

The flight population system generates realistic flight schedules by:

1. **Analyzing existing route data** to determine airport tiers and connectivity
2. **Applying flight frequency rules** based on airport importance and route demand
3. **Using realistic scheduling patterns** with peak/off-peak times and seasonal variations
4. **Generating appropriate flight numbers** and aircraft assignments

## Scripts

### 1. `flight_config.py`
Configuration file containing all flight generation rules and parameters.

**Features:**
- Airport tier definitions (Major Hub, Regional Hub, Secondary, Regional, Local)
- Seasonal multipliers (Winter: 0.85x, Summer: 1.3x, etc.)
- Day-of-week patterns (Friday: 1.3x, Saturday: 0.9x, etc.)
- Airline-specific operational patterns
- Aircraft selection rules by route type

**Usage:**
```bash
python scripts/flight_config.py  # View configuration summary
```

### 2. `test_flight_population.py`
Test suite to validate flight generation before full population.

**Tests:**
- Configuration validation
- Database connectivity and data availability
- Sample flight generation (1 week test)

**Usage:**
```bash
python scripts/test_flight_population.py
```

### 3. `populate_flights_simple.py`
Simplified flight population script for basic use cases.

**Features:**
- Basic frequency rules based on airport route counts
- Simple scheduling patterns
- Lightweight implementation

**Usage:**
```bash
python scripts/populate_flights_simple.py
```

### 4. `populate_flights_comprehensive.py`
Full-featured flight population script implementing all flight rules.

**Features:**
- Complete implementation of flight rules from `docs/flight_rules.md`
- Airport tier-based frequency calculation
- Realistic seasonal and day-of-week variations
- Airline-specific operational patterns
- Appropriate aircraft selection
- Batch processing for large datasets

**Usage:**
```bash
python scripts/populate_flights_comprehensive.py
```

### 5. `populate_flights.py`
Advanced flight population script with detailed route analysis.

**Features:**
- City population integration
- Distance-based flight duration calculation
- Advanced aircraft selection
- Comprehensive route analysis

## Flight Rules Implementation

Based on `docs/flight_rules.md`, the scripts implement:

### Airport Tiers
- **Tier 1 (Major Hub)**: 500+ routes → 6-12 daily flights
- **Tier 2 (Regional Hub)**: 200-499 routes → 2-6 daily flights  
- **Tier 3 (Secondary)**: 50-199 routes → 1-3 daily flights
- **Tier 4 (Regional)**: 10-49 routes → 3-7 weekly flights
- **Tier 5 (Local)**: 1-9 routes → 1-3 weekly flights

### Scheduling Patterns
- **Peak Hours**: 6-9 AM, 12-2 PM, 5-8 PM
- **Off-Peak Hours**: 10-11 AM, 2-5 PM, 8-11 PM
- **Night Hours**: 11 PM - 6 AM (limited service)

### Seasonal Adjustments
- **Summer**: +30% capacity (Jun-Aug)
- **Winter**: -15% capacity (Dec-Feb)
- **Spring/Fall**: Baseline capacity

### Day-of-Week Patterns
- **Monday/Friday**: +20-30% (business travel)
- **Tuesday-Thursday**: Baseline
- **Saturday**: -10% (leisure patterns)
- **Sunday**: Baseline (return travel)

## Prerequisites

1. **Database Setup**: Ensure your database contains:
   - Routes data (from OpenFlights or similar)
   - Airport data with IATA codes
   - Airline data with IATA codes
   - Aircraft/airplane data

2. **Environment**: 
   - Copy `.env.example` to `.env`
   - Configure database connection settings
   - Install dependencies: `uv sync`

## Usage Workflow

### 1. Test First
```bash
# Validate configuration and test with sample data
python scripts/test_flight_population.py
```

### 2. Choose Population Method

**For basic needs:**
```bash
python scripts/populate_flights_simple.py
```

**For comprehensive flight rules implementation:**
```bash
python scripts/populate_flights_comprehensive.py
```

### 3. Monitor Progress
The scripts provide progress updates and statistics during execution.

## Data Generated

### Flight Records
Each generated flight includes:
- **Flight Number**: Airline code + route-based number
- **Origin/Destination**: Airport IDs from route data
- **Departure/Arrival**: Realistic times with proper duration
- **Airline**: From route data
- **Aircraft**: Appropriate selection based on route characteristics

### Time Span
- **Default**: Last year + upcoming year (2-year total)
- **Customizable**: Any date range via script options

### Volume Estimates
Based on your route data (67,663 routes):
- **Conservative**: ~500,000-1,000,000 flights per year
- **Realistic**: ~2,000,000-5,000,000 flights per year
- **Peak periods**: +30% during summer months

## Performance Considerations

### Batch Processing
- Scripts use batch inserts (1,000 records per batch)
- Progress updates every month or major milestone
- Memory-efficient processing for large datasets

### Database Impact
- **Indexes**: Ensure indexes on departure, arrival, airport IDs
- **Storage**: Estimate ~100-200 bytes per flight record
- **Performance**: Consider running during off-peak hours

### Optimization Tips
1. **Start with test**: Always run test script first
2. **Incremental approach**: Start with shorter date ranges
3. **Monitor resources**: Watch database performance during population
4. **Backup first**: Backup database before large populations

## Troubleshooting

### Common Issues

**"No routes found"**
- Ensure route data is imported
- Check that routes have valid airport and airline codes

**"No aircraft found"**
- Import airplane/aircraft data
- Verify airplane table has records

**"Dependencies not available"**
- Run `uv sync` to install required packages
- Check Python path and imports

**Performance issues**
- Reduce batch size in scripts
- Use smaller date ranges
- Check database indexes

### Validation

After population, validate results:
```sql
-- Check flight distribution by airport
SELECT 
    a.name,
    COUNT(*) as flight_count
FROM flight f
JOIN airport a ON f.from_airport = a.airport_id
GROUP BY a.airport_id, a.name
ORDER BY flight_count DESC
LIMIT 20;

-- Check seasonal distribution
SELECT 
    EXTRACT(MONTH FROM departure) as month,
    COUNT(*) as flights
FROM flight
GROUP BY EXTRACT(MONTH FROM departure)
ORDER BY month;
```

## Support

For issues or questions:
1. Check the test script output for specific error messages
2. Verify database connectivity and data availability
3. Review the flight rules documentation in `docs/flight_rules.md`
4. Check script logs for detailed error information