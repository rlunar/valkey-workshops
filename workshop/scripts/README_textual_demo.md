# Textual Query Demo - Interactive Database Explorer

This interactive demo showcases the Flughafen DB database with progressively complex queries, from simple table selects to advanced multi-table joins implementing flight rules.

## Features

🎯 **Progressive Complexity**
- **Beginner**: Simple SELECT queries from single tables
- **Intermediate**: JOIN operations between related tables  
- **Advanced**: Complex multi-table queries with aggregations
- **Expert**: Flight rules implementation with geographic calculations

🔍 **Query Analysis**
- Real-time SQL display with syntax highlighting
- Query execution timing and row counts
- EXPLAIN plan analysis for performance insights
- Interactive results table with formatted data

✈️ **Flight Rules Implementation**
- Tier 1 hub airports (ATL, ORD, PEK, LHR, CDG, FRA, LAX, DFW, JFK, AMS)
- Distance-based flight categorization (short/medium/long-haul)
- Route frequency analysis following aviation best practices
- ATL to JFK route example (Tier 1 to Tier 1 connection)

## Installation

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure database**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Run the demo**:
   ```bash
   python scripts/textual_query_demo.py
   ```

## Available Queries

### Basic Queries
- **Simple Table Query**: Basic airport listing with IATA codes
- **City-Airport Relationships**: Geographic joins with population data

### Flight Rules Queries  
- **Tier 1 Hub Airports**: Major hubs with 500+ routes
- **ATL to JFK Routes**: Tier 1 to Tier 1 route analysis
- **Flight Frequency Analysis**: Distance-based frequency recommendations

### Advanced Analysis
- **Complex Route Analysis**: Multi-table joins with geographic, airline, and city data
- **International Route Patterns**: Cross-country flight analysis with population metrics

## Query Categories

### 🟢 Beginner (Green)
Simple single-table queries perfect for learning SQL basics.

### 🟡 Intermediate (Yellow) 
JOIN operations between 2-3 tables with basic filtering.

### 🔴 Advanced (Red)
Complex queries with multiple JOINs, aggregations, and subqueries.

### 🔴 Expert (Bold Red)
Advanced flight rules implementation with geographic calculations and business logic.

## Flight Rules Context

The demo implements real aviation industry practices:

- **Tier 1 Destinations**: 500+ routes (ATL, ORD, PEK, LHR, CDG, FRA, LAX, DFW, JFK, AMS)
- **Distance Categories**: 
  - Short-haul: 0-1,500km (high frequency, smaller aircraft)
  - Medium-haul: 1,500-4,000km (moderate frequency, narrow-body)
  - Long-haul: 4,000+km (lower frequency, wide-body aircraft)

## Technical Details

### Database Schema
- **Airport**: Core airport data (IATA, ICAO, names)
- **AirportGeo**: Geographic data (coordinates, timezone, country)
- **Flight**: Flight instances with timing and aircraft
- **Airline**: Airline information and codes
- **City**: Population and geographic city data
- **Route**: Route definitions and equipment

### Performance Features
- Query execution timing
- Row count reporting
- EXPLAIN plan analysis
- Indexed field usage optimization

## Usage Tips

1. **Start Simple**: Begin with basic queries to understand the schema
2. **Progress Gradually**: Move to intermediate joins before attempting expert queries
3. **Study the SQL**: Each query shows the actual SQL with syntax highlighting
4. **Check Performance**: Use EXPLAIN plans to understand query optimization
5. **Explore Results**: Interactive table allows scrolling through large result sets

## Troubleshooting

### Database Connection Issues
- Verify `.env` file configuration
- Check database server is running
- Confirm credentials and permissions

### Query Errors
- Check the SQL tab for syntax issues
- Verify table and column names exist
- Review EXPLAIN tab for optimization hints

### Performance Issues
- Use LIMIT clauses for large result sets
- Check indexes on frequently queried columns
- Consider query optimization based on EXPLAIN plans

## Example Workflow

1. **Start with "Simple Table Query"** to verify database connection
2. **Try "Tier 1 Hub Airports"** to see flight rules in action
3. **Explore "ATL to JFK Routes"** for real-world route analysis
4. **Advanced users**: Try "Complex Route Analysis" for comprehensive insights

The demo provides a hands-on way to understand both SQL query progression and real aviation industry data patterns.