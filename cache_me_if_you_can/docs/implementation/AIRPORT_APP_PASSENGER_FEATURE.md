# Airport App: Passenger Flights Feature

## Overview

Added a new feature to the Airport App that allows users to select a passenger and view all their flights using a complex 8-table JOIN query. This demonstrates the dramatic performance benefits of caching for complex database queries.

## New Features

### 1. Passenger Selection Dropdown

- **Random Passenger Pool**: Displays 10 random passengers with active bookings
- **Smart Display**: Shows passenger name, passport number, and booking count
- **Cached**: Passenger list is cached for 1 hour using `@st.cache_data`

**Example Display:**
```
John Doe (P103133) - 5 bookings
Jane Smith (P204567) - 3 bookings
...
```

### 2. Passenger Flights Query Button

New button: **"✈️ Get Passenger Flights (8-Table JOIN)"**

**Query Complexity:**
- 8 table JOINs
- Includes: booking, flight, airports (2x), airline, airplane, airplane_type, passenger
- Returns comprehensive flight information
- Limited to 10 most recent flights

**Data Returned:**
- Booking details (ID, seat, price)
- Flight information (number, departure, arrival times)
- Route details (departure/arrival airports with IATA codes)
- Airline information (name, IATA code)
- Aircraft details (type, capacity)
- Passenger information (name, passport)

### 3. Enhanced Data Display

**Main Table:**
- Booking ID
- Flight number
- Route (formatted as "JFK → LAX")
- Departure and arrival times
- Airline with IATA code
- Aircraft type with capacity
- Seat assignment
- Price (formatted with $)

**Detailed Statistics (Expandable):**
- Passenger name and passport
- Total flights found
- Total amount spent
- Number of unique airlines used
- Number of unique airports visited

## Implementation Details

### New Functions

#### `fetch_passenger_flights_db(passport_no)`
```python
def fetch_passenger_flights_db(passport_no):
    """Fetch all flights for a passenger (complex multi-table JOIN)"""
    # 8-table JOIN query
    # Returns comprehensive flight data
    # Ordered by departure date (most recent first)
    # Limited to 10 results
```

#### `get_random_passengers()`
```python
@st.cache_data(ttl=3600)
def get_random_passengers():
    """Get 10 random passengers with bookings"""
    # Cached for 1 hour
    # Only returns passengers with active bookings
    # Includes booking count for each passenger
```

### SQL Query

The passenger flights query performs 8 JOINs:

```sql
SELECT 
    b.booking_id,
    b.seat,
    b.price,
    f.flightno,
    f.departure,
    f.arrival,
    dep_airport.name AS departure_airport,
    dep_airport.iata AS departure_iata,
    arr_airport.name AS arrival_airport,
    arr_airport.iata AS arrival_iata,
    al.airlinename,
    al.iata AS airline_iata,
    at.identifier AS aircraft_type,
    ap.capacity AS aircraft_capacity,
    p.firstname,
    p.lastname,
    p.passportno
FROM booking b
JOIN flight f ON b.flight_id = f.flight_id
JOIN airport dep_airport ON f.`from` = dep_airport.airport_id
JOIN airport arr_airport ON f.`to` = arr_airport.airport_id
JOIN airline al ON f.airline_id = al.airline_id
JOIN airplane ap ON f.airplane_id = ap.airplane_id
JOIN airplane_type at ON ap.type_id = at.type_id
JOIN passenger p ON b.passenger_id = p.passenger_id
WHERE p.passportno = %s
ORDER BY f.departure DESC
LIMIT 10
```

### Cache Key Format

```python
cache_key = f"passenger_flights:{passport_no}"
```

Example: `passenger_flights:P103133`

## Performance Comparison

### Query Complexity Levels

| Query Type | Tables | JOINs | Typical DB Latency | Typical Cache Latency | Speedup |
|------------|--------|-------|-------------------|----------------------|---------|
| Flight Details | 3 | 3 | 50-100ms | 1-3ms | 20-50x |
| Flight Manifest | 3 | 3 | 80-150ms | 1-3ms | 30-80x |
| **Passenger Flights** | **8** | **8** | **150-300ms** | **1-5ms** | **50-200x** |

### Why This Matters

The 8-table JOIN query demonstrates:

1. **Complexity Impact**: More JOINs = exponentially slower queries
2. **Cache Benefits**: Complex queries benefit most from caching
3. **Real-World Scenario**: Typical e-commerce/booking system query
4. **Dramatic Speedup**: 50-200x faster with cache

## UI/UX Improvements

### Visual Hierarchy

```
Query Controls
├── Flight ID Input
├── [Get Flight Details] (3 JOINs)
├── [Get Manifest] (3 JOINs)
├── Passenger Selection
│   └── Dropdown with 10 random passengers
├── [Get Passenger Flights] (8 JOINs) ← NEW
└── [Flush Cache]
```

### Color Coding in Chart

- **Green**: Valkey Cache
- **Light Red**: Database (simple)
- **Medium Red**: Database (3 JOINs)
- **Dark Red**: Database (8 JOINs) ← Most dramatic difference

### User Feedback

- ✅ Success messages with passenger name
- 📊 Expandable detailed statistics
- 🎨 Formatted data display (routes, prices, etc.)
- ⚠️ Clear error messages

## Usage Example

### Step-by-Step

1. **Open the app**: `./scripts/run_airport_app.sh`

2. **Select a passenger** from the dropdown:
   ```
   John Doe (P103133) - 5 bookings
   ```

3. **Click "Get Passenger Flights"**:
   - First click: Database query (~200ms)
   - Shows all flights for John Doe
   - Displays comprehensive flight information

4. **Click again**:
   - Cache hit (~2ms)
   - **100x faster!**

5. **Compare in chart**:
   - See the dramatic difference between database and cache
   - Notice 8-table JOIN is slowest database query
   - But fastest when cached!

## Benefits

### For Users

- **Comprehensive View**: See all passenger flights in one query
- **Fast Response**: Subsequent queries are instant
- **Rich Information**: Complete flight details including aircraft type
- **Easy Selection**: Random passenger pool for quick testing

### For Developers

- **Real-World Example**: Demonstrates typical complex query
- **Performance Metrics**: Clear visualization of cache benefits
- **Best Practices**: Shows proper cache key design
- **Scalability**: Proves caching is essential for complex queries

### For Demonstrations

- **Dramatic Impact**: 8-table JOIN shows biggest speedup
- **Visual Proof**: Chart clearly shows performance difference
- **Business Value**: Demonstrates ROI of caching infrastructure
- **Scalability Story**: Shows how caching enables complex features

## Technical Notes

### Caching Strategy

- **TTL**: 3600 seconds (1 hour)
- **Key Format**: `passenger_flights:{passport_no}`
- **Invalidation**: Manual via "Flush Cache" button
- **Passenger List**: Cached separately with `@st.cache_data`

### Database Optimization

The query is optimized with:
- Proper JOIN order (smallest tables first)
- LIMIT clause to prevent large result sets
- ORDER BY on indexed column (departure)
- WHERE clause on indexed column (passportno)

### Error Handling

- Validates passenger selection before query
- Try-catch blocks around database operations
- User-friendly error messages
- Graceful handling of missing data

## Future Enhancements

Potential improvements:

1. **Date Range Filter**: Filter flights by date range
2. **Airline Filter**: Show flights for specific airline
3. **Route Filter**: Filter by departure/arrival airport
4. **Export Feature**: Download flight history as CSV
5. **Statistics Dashboard**: Aggregate passenger travel statistics
6. **Comparison View**: Compare multiple passengers
7. **Cache Warming**: Pre-populate cache for frequent passengers
8. **Smart Invalidation**: Invalidate cache when bookings change

## Testing

### Test Scenarios

1. **First Query**: Verify database latency (150-300ms)
2. **Second Query**: Verify cache hit (1-5ms)
3. **Different Passengers**: Verify cache miss for new passenger
4. **Flush Cache**: Verify cache invalidation works
5. **No Flights**: Test passenger with no bookings
6. **Error Handling**: Test with invalid passport number

### Performance Benchmarks

Expected latencies:
- Database (cold): 150-300ms
- Database (warm): 100-200ms
- Cache (hit): 1-5ms
- Speedup: 50-200x

## Conclusion

The passenger flights feature demonstrates the dramatic performance benefits of caching for complex database queries. The 8-table JOIN query is a realistic example of queries found in production systems, and the 50-200x speedup clearly shows why caching is essential for scalable applications.

This feature completes the demonstration of caching benefits across three complexity levels:
- Simple (3 JOINs)
- Medium (3 JOINs with more data)
- Complex (8 JOINs with comprehensive data)

Users can now see firsthand how caching transforms slow, complex queries into instant responses, enabling rich features that would otherwise be impractical.
