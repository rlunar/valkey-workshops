# SQL Query Samples for Flughafen Airport Database

This directory contains example SQL queries organized by complexity level, demonstrating various database operations on the airport database schema.

## Files Overview

### 01_simple_queries.sql
**Single table operations** - Basic SELECT statements with simple filtering.

Examples:
- Fetch airline by ID or IATA code
- Get airport by ICAO/IATA code
- Find airports by name pattern
- Count passengers and bookings
- Get employee by username

**Use cases:** Quick lookups, data validation, simple reports

---

### 02_medium_queries.sql
**Joins and filtering** - Queries involving 2-3 table joins with filtering.

Examples:
- Get passenger with their details (passenger + passengerdetails)
- Find passengers by country and/or passport
- Get flights with airline information
- Get flights between specific airports
- Count bookings per passenger
- Get airplane with type information

**Use cases:** User profiles, search functionality, basic analytics

---

### 03_advanced_queries.sql
**Complex joins and aggregations** - Multi-table joins (4+ tables) with analytics.

Key queries:

1. **Last 10 Passenger Bookings** - Complete booking history with:
   - Passenger information
   - Flight details (number, departure, arrival)
   - Departure airport (name, IATA code)
   - Arrival airport (name, IATA code)
   - Airline information

2. **Passenger's Complete Booking History** - All bookings for a specific passenger

3. **Upcoming Flights** - Future flights with passenger, airport, and airplane details

4. **Flight Manifest** - All passengers on a specific flight with seat assignments

5. **Revenue Analysis by Route** - Top routes by revenue with statistics

6. **Passenger Travel Statistics** - Frequent flyers with spending patterns

7. **Detailed Flight Information** - Complete flight data including:
   - Duration calculation
   - Geographic information (cities, countries)
   - Seat availability
   - Airplane type and capacity

8. **Busiest Routes** - Routes ranked by passenger count

9. **Airline Performance Summary** - Fleet size, revenue, and efficiency metrics

10. **Recent Bookings with Geography** - Latest bookings with full geographic context

**Use cases:** Business intelligence, reporting dashboards, customer analytics, operational insights

---

## Query Complexity Comparison

| Level | Tables Joined | Aggregations | Subqueries | Use Case |
|-------|--------------|--------------|------------|----------|
| Simple | 1 | None | None | Lookups, validation |
| Medium | 2-3 | Basic (COUNT) | None | Search, profiles |
| Advanced | 4+ | Multiple (SUM, AVG, COUNT) | Optional | Analytics, BI |

## Performance Considerations

### Indexed Columns (from schema)
- `airport.iata`, `airport.icao`, `airport.name`
- `airline.iata`, `airline.base_airport`
- `flight.from`, `flight.to`, `flight.departure`, `flight.arrival`
- `booking.flight_id`, `booking.passenger_id`
- `passenger.passportno`

### Tips for Production Use
1. Always use `LIMIT` for exploratory queries
2. Add indexes on frequently filtered columns
3. Use `EXPLAIN` to analyze query performance
4. Consider caching results for expensive aggregations
5. Use prepared statements to prevent SQL injection

## Testing Queries

Replace placeholder values:
- `passenger_id = 1000` → Use actual passenger ID
- `flight_id = 115` → Use actual flight ID
- `airline_id = 1` → Use actual airline ID
- `'JFK'`, `'FRA'` → Use actual airport codes

## Integration with Valkey Cache

These queries are ideal candidates for caching:
- **Simple queries**: Cache for 1 hour (rarely change)
- **Medium queries**: Cache for 15-30 minutes
- **Advanced queries**: Cache for 5-10 minutes (or invalidate on booking)

See `airport_app.py` for cache-aside pattern implementation.
