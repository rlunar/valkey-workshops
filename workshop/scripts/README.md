# FlughafenDB Population Scripts

This directory contains scripts for populating the FlughafenDB database with realistic test data.

## Passenger Population Script

### Overview

The `populate_passengers.py` script generates realistic passenger data with geographic distributions that reflect real-world travel patterns. The script creates 10 million passenger records by default, with distributions favoring:

- Major metropolitan areas and business hubs
- Economically developed countries with high travel volumes
- Popular international travel destinations
- Realistic age distributions (peak at 25-45 for business travelers)

### Geographic Distribution

The script uses weighted distributions based on travel statistics:

**High Volume (>5% each):**
- United States (25.0%) - Major cities like NYC, LA, Chicago
- United Kingdom (8.5%) - London, Manchester, Birmingham
- China (8.2%) - Beijing, Shanghai, Shenzhen
- Germany (7.8%) - Berlin, Munich, Frankfurt
- France (6.9%) - Paris, Lyon, Marseille
- Japan (6.5%) - Tokyo, Osaka, Yokohama

**Medium Volume (2-5% each):**
- Italy, Spain, Australia, South Korea, India, Brazil, Canada, Saudi Arabia

**Lower Volume (1-2% each):**
- Netherlands, Sweden, Russia, Norway, Denmark, Finland

### Quick Start

#### Unified Tool (Recommended)
```bash
# Show all available options
python scripts/passenger_tools.py help

# Generate 10M records (default)
python scripts/passenger_tools.py populate

# Test with small dataset first
python scripts/passenger_tools.py test

# Monitor progress during population
python scripts/passenger_tools.py monitor

# Validate data quality after completion
python scripts/passenger_tools.py validate
```

### Usage

#### Full Population (10 Million Records)
```bash
# Default: 10 million records in batches of 10,000
python scripts/populate_passengers.py

# Custom parameters
python scripts/populate_passengers.py --total-records 5000000 --batch-size 5000
```

#### Test Run (Small Dataset)
```bash
# Test with 1,000 records
python scripts/test_passenger_generation.py
```

#### Monitor Progress
```bash
# Monitor progress with default settings (check every 30 seconds)
python scripts/monitor_population.py

# Custom monitoring
python scripts/monitor_population.py --target 5000000 --interval 60

# Get current statistics only
python scripts/monitor_population.py --stats-only
```

#### Validate Data Quality
```bash
# Run comprehensive data validation and analysis
python scripts/validate_passenger_data.py
```

### Parameters

- `--total-records`: Number of records to generate (default: 10,000,000)
- `--batch-size`: Batch size for database inserts (default: 10,000, max: 50,000)

### Prerequisites

1. **Database Setup**: Ensure your database is configured in `.env` file
2. **Dependencies**: Install required packages:
   ```bash
   pip install faker
   # or if using uv:
   uv add faker
   ```

### Performance Considerations

- **Memory Usage**: The script processes data in batches to manage memory efficiently
- **Database Performance**: Larger batch sizes are faster but use more memory
- **Estimated Runtime**: ~2-4 hours for 10 million records (depends on database performance)
- **Storage**: Approximately 2-3 GB of database storage for 10 million records

### Data Characteristics

**Passenger Table:**
- Unique passport numbers (2 letters + 7 digits)
- Realistic first/last names using locale-appropriate Faker instances
- Primary key auto-generated

**PassengerDetails Table:**
- Age distribution: 18-80 years, weighted toward 25-45 (business travelers)
- Gender: Random M/F distribution
- Addresses: Locale-appropriate street addresses
- Contact Info: 85% have email, 75% have phone numbers
- Geographic distribution matches travel patterns

### Example Output

```
Starting passenger population: 10,000,000 records in batches of 10,000
Processing batch 1/1000 (10,000 records)...
Progress: 10,000/10,000,000 (0.1%)
Processing batch 2/1000 (10,000 records)...
Progress: 20,000/10,000,000 (0.2%)
...

Completed! Inserted 10,000,000 passenger records.

Geographic Distribution Summary:
  United States: ~2,500,000 passengers (25.0%)
  United Kingdom: ~850,000 passengers (8.5%)
  China: ~820,000 passengers (8.2%)
  Germany: ~780,000 passengers (7.8%)
  ...
```

### Error Handling

The script includes comprehensive error handling for:
- Database connection issues
- Memory constraints
- Duplicate passport number generation
- Batch processing failures

### Monitoring Progress

The script provides real-time progress updates including:
- Current batch being processed
- Total records inserted
- Percentage completion
- Geographic distribution summary at completion

## Booking Population System

### Overview

The booking population system generates realistic airline booking data that follows industry patterns and business rules. It creates bookings that respect aircraft capacity, prevent passenger conflicts, and implement sophisticated occupancy patterns.

### Key Features

**🎯 Realistic Occupancy Patterns**
- Peak times (90-95% occupancy): Business hours, weekdays, holidays
- Off-peak times (60-75% occupancy): Nights, weekends, regular periods
- Dynamic calculation based on departure timing

**👥 Passenger Management**
- No double-booking: Prevents overlapping flight conflicts
- 2-hour buffer for connections
- Automatic passenger pool management

**✈️ Business vs Leisure Travel**
- Business travelers: 85% book returns (1-7 days)
- Leisure travelers: 70% book returns (3-21 days)
- Realistic timing preferences

**💺 Seat Assignment System**
- Aircraft-appropriate seat maps
- Class distribution: 85% economy, 12% business, 3% first
- Unique seat assignments per flight

**💰 Dynamic Pricing**
- Distance-based pricing ($0.15/km base)
- Class multipliers (economy 1x, business 3.5x, first 6x)
- Peak time surcharge (30%)
- Return flight discount (10%)

### Quick Start

```bash
# Basic booking population
python scripts/populate_bookings.py

# Clear existing bookings first
python scripts/populate_bookings.py --clear

# Test the logic with sample data
python scripts/test_booking_population.py

# Validate booking data integrity
python scripts/validate_booking_system.py
```

### Usage Options

```bash
# Custom batch size for performance tuning
python scripts/populate_bookings.py --batch-size 5000

# Enable verbose output for debugging
python scripts/populate_bookings.py --verbose

# Full workflow
python scripts/populate_bookings.py --clear --verbose
```

### Prerequisites

Before running booking population:
1. Populated `flight` table
2. Populated `passenger` table
3. Populated `airplane` table (for capacity data)
4. Database tables created via `setup_database.py`

### Performance Characteristics

- **Processing Rate**: 1,000-5,000 bookings/second
- **Memory Usage**: Moderate (tracks passenger conflicts)
- **Database Load**: Optimized batch inserts

### Data Quality Assurance

The system enforces strict business rules:
- No overbooking (never exceeds aircraft capacity)
- No double-booking (passengers can't be in two places at once)
- Realistic occupancy following airline industry patterns
- Market-realistic ticket pricing
- Valid seat assignments for each aircraft type

### Validation and Monitoring

```bash
# Comprehensive validation
python scripts/validate_booking_system.py
```

Checks include:
- Duplicate seat detection
- Occupancy rate analysis
- Price distribution validation
- Peak vs off-peak patterns
- Passenger booking frequency

### Documentation

For detailed information, see:
- `scripts/README_booking_population.md` - Complete system documentation
- `scripts/test_booking_population.py` - Logic validation
- `scripts/validate_booking_system.py` - Data integrity checks