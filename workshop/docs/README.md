# Cache Me, If You Can: Valkey Edition

A comprehensive hands-on guide to explore caching strategies with Valkey through practical database queries and real-world aviation data analysis.

## Overview

This guide demonstrates key concepts from simple database queries to complex caching scenarios using the FlughafenDB aviation database. You'll learn to:

1. Execute basic SQL queries using command-line tools
2. Analyze query performance with EXPLAIN commands
3. Implement caching strategies with Valkey
4. Monitor cache performance and behavior

### Database Schema

![FlughafenDB-schema](../static/FlughafenDB-schema.png)

```mermaid
graph TB
    subgraph "Core Aviation Entities"
        A[Airport] --> AG[Airport_Geo]
        AL[Airline] --> F[Flight]
        AT[Airplane_Type] --> AP[Airplane]
        C[Country] --> CT[City]
        CT --> AG
    end
    
    subgraph "Flight Operations"
        F --> R[Route]
        F --> FL[Flight_Log]
        F --> FS[Flight_Schedule]
        AP --> F
        A --> F
    end
    
    subgraph "Passenger Management"
        P[Passenger] --> B[Booking]
        B --> F
        E[Employee] --> AL
    end
    
    subgraph "Weather & Geography"
        W[Weather] --> A
        AG --> A
    end
    
    style A fill:#e1f5fe
    style F fill:#f3e5f5
    style P fill:#e8f5e8
    style B fill:#fff3e0
```

## Prerequisites

Before starting, ensure you have:
- Database server running (MySQL/MariaDB/PostgreSQL)
- [Valkey](https://valkey.io/) server running
- Command-line tools installed: `mycli`/`pgcli` and `valkey-cli`
- [FlughafenDB](https://github.com/stefanproell/flughafendb/) data populated (see main README.md)

## Workshop Structure

```mermaid
flowchart LR
    subgraph "Part 1: Database Fundamentals"
        A1[Basic Queries] --> A2[Performance Analysis]
        A2 --> A3[EXPLAIN Commands]
        A3 --> A4[Identify Expensive Operations]
    end
    
    subgraph "Part 2: Caching Introduction"
        B1[Valkey Operations] --> B2[Cache-Aside Pattern]
        B2 --> B3[Performance Monitoring]
    end
    
    subgraph "Part 3: Advanced Patterns"
        C1[Write-Through] --> C2[Write-Behind]
        C2 --> C3[Cache Invalidation]
        C3 --> C4[Real-World Scenarios]
    end
    
    A4 --> B1
    B3 --> C1
    
    style A1 fill:#e3f2fd
    style B1 fill:#f1f8e9
    style C1 fill:#fce4ec
```

### Part 1: Database Fundamentals
- Basic queries and performance analysis
- Understanding query costs with `EXPLAIN`
- Identifying expensive operations

### Part 2: Caching Introduction
- Basic Valkey operations
- Cache-aside pattern implementation
- Performance monitoring

### Part 3: Advanced Caching Patterns
- Write-through and write-behind patterns
- Cache invalidation strategies
- Real-world scenarios

## Part 1: Database Query Fundamentals

### Step 1: Connect to Your Database

First, connect to your database using the appropriate CLI tool:

**For MySQL/MariaDB:**

```bash
# Connect using mycli (enhanced MySQL client)
mycli -u flughafen_user -p -D flughafendb

# Or using standard mysql client
mysql -u flughafen_user -p flughafendb
```

**For PostgreSQL:**
```bash
# Connect using pgcli (enhanced PostgreSQL client)
pgcli -U flughafen_user -d flughafendb

# Or using standard psql client
psql -U flughafen_user -d flughafendb
```

### Step 2: Explore the Database Structure

Let's start by understanding what data we have:

```sql
-- Show all tables in the database
SHOW TABLES;  -- MySQL/MariaDB
-- or
\dt           -- PostgreSQL

-- Examine the airport table structure
DESCRIBE airport;     -- MySQL/MariaDB
-- or
\d airport           -- PostgreSQL
```

**Expected Output:**

```
+-----------------------+
| Tables_in_flughafendb |
+-----------------------+
| airline               |
| airplane              |
| airplane_type         |
| airport               |
| airport_geo           |
| airport_reachable     |
| booking               |
| city                  |
| city_airport_relation |
| country               |
| employee              |
| flight                |
| flight_log            |
| flightschedule        |
| passenger             |
| passengerdetails      |
| route                 |
| weatherdata           |
+-----------------------+
```

### Step 3: Simple Query - Find Airports by Country and City

Let's start with a basic query to find airports in a specific country 🇩🇪:

```sql
-- Find first 10 airports by name (alphabetically) in Germany (Deutschland)
SELECT
    a.name,
    a.iata,
    a.icao,
    ag.city,
    ag.country, 
    ag.iso_a3
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE a.iata IS NOT null 
    AND ag.iso_a3 = 'DEU'
ORDER BY a.name
LIMIT 10 OFFSET 0;
```

**Expected Output:**

```bash
+----------------------------------------+------+------+-------------+---------+--------+
| name                                   | iata | icao | city        | country | iso_a3 |
+----------------------------------------+------+------+-------------+---------+--------+
| [Duplicate] Giebelstadt Army Air Field | GHF  | ETEU | Giebelstadt | Germany | DEU    |
| Aachen-Merzbrück Airport               | AAH  | EDKA | Aachen      | Germany | DEU    |
| Altenburg-Nobitz Airport               | AOC  | EDAC | Altenburg   | Germany | DEU    |
| Augsburg Airport                       | AGB  | EDMA | Augsburg    | Germany | DEU    |
| Baltrum Airport                        | BMR  | EDWZ | Baltrum     | Germany | DEU    |
| Barth Airport                          | BBH  | EDBH | Barth       | Germany | DEU    |
| Bayreuth Airport                       | BYU  | EDQD | Bayreuth    | Germany | DEU    |
| Berlin-Schönefeld Airport              | SXF  | EDDB | Berlin      | Germany | DEU    |
| Berlin-Tegel Airport                   | TXL  | EDDT | Berlin      | Germany | DEU    |
| Berlin-Tempelhof International Airport | THF  | EDDI | Berlin      | Germany | DEU    |
+----------------------------------------+------+------+-------------+---------+--------+
```

If we want to be more specific to find airports in New York City 🗽.

```sql
-- Find all airports in New York City
SELECT
    a.name,
    a.iata,
    a.icao,
    ag.city,
    ag.country, 
    ag.iso_a3
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE a.iata IS NOT null 
    AND ag.iso_a3 = 'USA' 
    AND ag.city LIKE "%New York%"
ORDER BY a.name
LIMIT 10 OFFSET 0;
```

**Expected Output:**

```bash
+--------------------------------------+------+------+----------+---------------+--------+
| name                                 | iata | icao | city     | country       | iso_a3 |
+--------------------------------------+------+------+----------+---------------+--------+
| Downtown-Manhattan/Wall St Heliport  | JRB  | KJRB | New York | United States | USA    |
| John F Kennedy International Airport | JFK  | KJFK | New York | United States | USA    |
| La Guardia Airport                   | LGA  | KLGA | New York | United States | USA    |
| West 30th St. Heliport               | JRA  | KJRA | New York | United States | USA    |
+--------------------------------------+------+------+----------+---------------+--------+
```

**Expected Output:**
```
+--------------------------------+------+------+----------+---------+
| name                          | iata | icao | city     | country |
+--------------------------------+------+------+----------+---------+
| Berlin Brandenburg Airport    | BER  | EDDB | Berlin   | Germany |
| Cologne Bonn Airport         | CGN  | EDDK | Cologne  | Germany |
| Dortmund Airport             | DTM  | EDLW | Dortmund | Germany |
| Dresden Airport              | DRS  | EDDC | Dresden  | Germany |
| Düsseldorf Airport           | DUS  | EDDL | Dusseldorf| Germany |
+--------------------------------+------+------+----------+---------+
```

### Step 4: Analyze Query Performance

Now let's see how expensive this query is:

```sql
-- Analyze the query execution plan
EXPLAIN SELECT 
    a.name,
    a.iata,
    a.icao,
    ag.city,
    ag.country
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE ag.country = 'Germany'
ORDER BY a.name
LIMIT 10;
```

```mermaid
graph TD
    subgraph "Query Execution Plan"
        A[Start Query] --> B{Check Index}
        B -->|No Index| C[Full Table Scan<br/>7,698 rows]
        B -->|Index Available| D[Index Lookup<br/>~10 rows]
        C --> E[Filter by Country<br/>~770 rows]
        D --> E
        E --> F[Join with Airport Table<br/>1:1 relationship]
        F --> G[Sort by Name<br/>Using filesort]
        G --> H[Limit 10 results]
        H --> I[Return Results]
    end
    
    subgraph "Performance Impact"
        J[Without Index:<br/>Expensive O(n)]
        K[With Index:<br/>Efficient O(log n)]
        L[With Cache:<br/>O(1)]
    end
    
    C -.-> J
    D -.-> K
    I -.-> L
    
    style C fill:#ffcdd2
    style D fill:#c8e6c9
    style L fill:#e1f5fe
```

**Expected Output (MySQL):**
```
+----+-------------+-------+------------+------+---------------+---------+---------+--------------------+------+----------+-----------------------------+
| id | select_type | table | partitions | type | possible_keys | key     | key_len | ref                | rows | filtered | Extra                       |
+----+-------------+-------+------------+------+---------------+---------+---------+--------------------+------+----------+-----------------------------+
|  1 | SIMPLE      | ag    | NULL       | ALL  | PRIMARY       | NULL    | NULL    | NULL               | 7698 |    10.00 | Using where; Using filesort |
|  1 | SIMPLE      | a     | NULL       | eq_ref| PRIMARY       | PRIMARY | 4       | flughafendb.ag.airport_id | 1 |   100.00 | NULL                        |
+----+-------------+-------+------------+------+---------------+---------+---------+--------------------+------+----------+-----------------------------+
```

**Analysis:**
- The query scans all 7,698 rows in `airport_geo` table (type: ALL)
- No index is used for the country filter
- This is an expensive operation that would benefit from caching

### Step 5: More Complex Query - Find Airports by IATA Code

Let's try a query that should be more efficient:

```sql
-- Find airport details by IATA code
SELECT 
    a.name,
    a.iata,
    a.icao,
    ag.city,
    ag.country,
    ag.latitude,
    ag.longitude,
    ag.altitude
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE a.iata = 'JFK';
```

**Expected Output:**
```
+-------------------------------+------+------+----------+---------+-----------+------------+----------+
| name                         | iata | icao | city     | country | latitude  | longitude  | altitude |
+-------------------------------+------+------+----------+---------+-----------+------------+----------+
| John F Kennedy International | JFK  | KJFK | New York | USA     | 40.639751 | -73.778925 |      13  |
+-------------------------------+------+------+----------+---------+-----------+------------+----------+
```

Now let's analyze this query:

```sql
EXPLAIN SELECT 
    a.name,
    a.iata,
    a.icao,
    ag.city,
    ag.country,
    ag.latitude,
    ag.longitude,
    ag.altitude
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE a.iata = 'JFK';
```

**Expected Output (MySQL):**
```
+----+-------------+-------+------------+------+---------------+------+---------+--------------------+------+----------+-------+
| id | select_type | table | partitions | type | possible_keys | key  | key_len | ref                | rows | filtered | Extra |
+----+-------------+-------+------------+------+---------------+------+---------+--------------------+------+----------+-------+
|  1 | SIMPLE      | a     | NULL       | ref  | iata          | iata | 4       | const              |    1 |   100.00 | NULL  |
|  1 | SIMPLE      | ag    | NULL       | eq_ref| PRIMARY      | PRIMARY| 4     | flughafendb.a.airport_id| 1 |   100.00 | NULL  |
+----+-------------+-------+------------+------+---------------+------+---------+--------------------+------+----------+-------+
```

**Analysis:**
- Much more efficient! Uses index on IATA code (type: ref)
- Only examines 1 row instead of scanning the entire table
- This query is fast and might not need caching

## Part 2: Introduction to Valkey Caching

### Step 6: Connect to Valkey

Open a new terminal and connect to your Valkey server:

```bash
# Connect to Valkey CLI
valkey-cli

# Test the connection
127.0.0.1:6379> PING
PONG

# Check server info
127.0.0.1:6379> INFO server
```

### Step 7: Basic Valkey Operations

Let's learn the fundamental Valkey commands:

```bash
# Set a simple key-value pair
127.0.0.1:6379> SET airport:JFK:name "John F Kennedy International"
OK

# Get the value
127.0.0.1:6379> GET airport:JFK:name
"John F Kennedy International"

# Set with expiration (TTL of 300 seconds)
127.0.0.1:6379> SETEX airport:JFK:city 300 "New York"
OK

# Check TTL
127.0.0.1:6379> TTL airport:JFK:city
(integer) 295

# Store complex data as JSON
127.0.0.1:6379> SET airport:JFK:details '{"name":"John F Kennedy International","iata":"JFK","icao":"KJFK","city":"New York","country":"USA","latitude":40.639751,"longitude":-73.778925,"altitude":13}'
OK

# Retrieve and view JSON data
127.0.0.1:6379> GET airport:JFK:details
"{\"name\":\"John F Kennedy International\",\"iata\":\"JFK\",\"icao\":\"KJFK\",\"city\":\"New York\",\"country\":\"USA\",\"latitude\":40.639751,\"longitude\":-73.778925,\"altitude\":13}"
```

### Step 8: Monitor Valkey Activity

Open another terminal and start monitoring Valkey operations:

```bash
# Start monitoring all commands
valkey-cli MONITOR
```

Keep this terminal open - you'll see all Valkey operations in real-time as we proceed.

### Step 9: Implement Cache-Aside Pattern

Now let's implement a simple cache-aside pattern. In your database terminal, let's simulate checking cache first:

```mermaid
sequenceDiagram
    participant App as Application
    participant Cache as Valkey Cache
    participant DB as Database
    
    Note over App,DB: Cache-Aside Pattern Flow
    
    App->>Cache: 1. GET airport:country:Germany
    Cache-->>App: (nil) - Cache Miss
    
    App->>DB: 2. SELECT airports WHERE country='Germany'
    DB-->>App: Airport data (500ms)
    
    App->>Cache: 3. SETEX airport:country:Germany 300 [data]
    Cache-->>App: OK
    
    App-->>App: Return data to user
    
    Note over App,DB: Subsequent Request
    
    App->>Cache: 4. GET airport:country:Germany
    Cache-->>App: [cached data] (1ms) - Cache Hit!
    
    App-->>App: Return cached data
    
    Note over Cache: TTL: 300 seconds
```

**Step 9a: Check Cache First**
```bash
# In Valkey CLI - check if data exists in cache
127.0.0.1:6379> GET airport:country:Germany
(nil)
```

**Step 9b: Cache Miss - Query Database**
Since the cache is empty, we need to query the database:

```sql
-- Back in your database CLI
SELECT 
    a.name,
    a.iata,
    a.icao,
    ag.city
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE ag.country = 'Germany'
ORDER BY a.name
LIMIT 5;
```

**Step 9c: Store Result in Cache**
```bash
# In Valkey CLI - store the result with 5-minute TTL
127.0.0.1:6379> SETEX airport:country:Germany 300 '[{"name":"Berlin Brandenburg Airport","iata":"BER","icao":"EDDB","city":"Berlin"},{"name":"Cologne Bonn Airport","iata":"CGN","icao":"EDDK","city":"Cologne"},{"name":"Dortmund Airport","iata":"DTM","icao":"EDLW","city":"Dortmund"},{"name":"Dresden Airport","iata":"DRS","icao":"EDDC","city":"Dresden"},{"name":"Düsseldorf Airport","iata":"DUS","icao":"EDDL","city":"Dusseldorf"}]'
OK
```

**Step 9d: Subsequent Cache Hit**
```bash
# Next request - cache hit!
127.0.0.1:6379> GET airport:country:Germany
"[{\"name\":\"Berlin Brandenburg Airport\",\"iata\":\"BER\",\"icao\":\"EDDB\",\"city\":\"Berlin\"}...]"
```

### Step 10: Performance Comparison

Let's measure the performance difference:

**Database Query Time:**
```sql
-- Time the database query
SELECT BENCHMARK(1, (
    SELECT COUNT(*) 
    FROM airport a
    JOIN airport_geo ag ON a.airport_id = ag.airport_id
    WHERE ag.country = 'Germany'
));
```

**Cache Retrieval Time:**
```bash
# Time the cache retrieval
127.0.0.1:6379> DEBUG OBJECT airport:country:Germany
Value at:0x7f8b8c0a5a40 refcount:1 encoding:embstr serializedlength:445 lru:15728640 lru_seconds_idle:10
```

**Observation:** Cache retrieval is typically 10-100x faster than database queries.

## Part 3: User-Facing Query Scenarios

### Step 11: Flight Search - Find Available Flights

This is the most common and expensive query in any flight booking system. Let's implement flight search with caching:

```mermaid
graph TB
    subgraph "Flight Search Architecture"
        U[User Request<br/>JFK → LAX<br/>2025-12-15] --> C{Check Cache}
        C -->|Hit| CR[Return Cached Results<br/>~1ms]
        C -->|Miss| DB[(Database Query)]
        
        DB --> Q1[Join Flight Table]
        Q1 --> Q2[Join Airport Tables]
        Q2 --> Q3[Join Airline Table]
        Q3 --> Q4[Join Booking Table]
        Q4 --> Q5[Filter by Route & Date]
        Q5 --> Q6[Group & Aggregate]
        Q6 --> Q7[Sort by Departure]
        Q7 --> R[Results ~200-500ms]
        
        R --> SC[Store in Cache<br/>TTL: 5-15 min]
        SC --> CR
    end
    
    subgraph "Query Complexity"
        QC1[4 Table Joins]
        QC2[Date Functions]
        QC3[Aggregations]
        QC4[Subqueries]
    end
    
    style U fill:#e3f2fd
    style CR fill:#e8f5e8
    style DB fill:#ffecb3
    style R fill:#ffcdd2
```

**Use Case:** User searches for flights from JFK to LAX on a specific date

```sql
-- Find available flights for a route and date (expensive query)
SELECT 
    f.flight_id,
    f.flightno,
    al.name as airline_name,
    al.iata as airline_code,
    dep_a.name as departure_airport,
    dep_a.iata as dep_iata,
    arr_a.name as arrival_airport,
    arr_a.iata as arr_iata,
    f.departure,
    f.arrival,
    TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as duration_minutes,
    COUNT(b.booking_id) as booked_seats,
    (SELECT COUNT(*) FROM booking WHERE flight_id = f.flight_id) as total_bookings
FROM flight f
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airline al ON f.airline_id = al.airline_id
LEFT JOIN booking b ON f.flight_id = b.flight_id
WHERE dep_a.iata = 'JFK' 
    AND arr_a.iata = 'LAX'
    AND DATE(f.departure) = '2025-12-15'
GROUP BY f.flight_id, f.flightno, al.name, al.iata, dep_a.name, dep_a.iata, 
         arr_a.name, arr_a.iata, f.departure, f.arrival
ORDER BY f.departure;
```

**Analyze the query cost:**
```sql
EXPLAIN SELECT 
    f.flight_id,
    f.flightno,
    al.name as airline_name,
    dep_a.iata as dep_iata,
    arr_a.iata as arr_iata,
    f.departure,
    f.arrival,
    COUNT(b.booking_id) as booked_seats
FROM flight f
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airline al ON f.airline_id = al.airline_id
LEFT JOIN booking b ON f.flight_id = b.flight_id
WHERE dep_a.iata = 'JFK' 
    AND arr_a.iata = 'LAX'
    AND DATE(f.departure) = '2025-12-15'
GROUP BY f.flight_id
ORDER BY f.departure;
```

**Expected Analysis:**
- Multiple table joins (4 tables)
- Date function on indexed column (expensive!)
- GROUP BY with aggregation
- Subquery for booking count
- **Very expensive** - perfect for caching!

### Step 12: Cache Flight Search Results

Let's implement intelligent caching for flight searches:

```mermaid
graph LR
    subgraph "Cache Key Strategy"
        A[flight:search] --> B[JFK]
        B --> C[LAX]
        C --> D[2025-12-15]
        D --> E[flight:search:JFK:LAX:2025-12-15]
    end
    
    subgraph "Popular Routes Cache"
        F[ZADD popular:routes] --> G[Score: Frequency]
        G --> H[JFK:LAX: 1500]
        G --> I[LAX:JFK: 1200]
        G --> J[JFK:LHR: 1100]
    end
    
    subgraph "Cache Hierarchy"
        K[Route Level<br/>TTL: 5-15 min] --> L[Flight Details<br/>TTL: 2-5 min]
        L --> M[Seat Availability<br/>TTL: 30s-2min]
    end
    
    style E fill:#e1f5fe
    style H fill:#f3e5f5
    style K fill:#e8f5e8
```

```bash
# Cache flight search results with structured key
127.0.0.1:6379> SET flight:search:JFK:LAX:2025-12-15 '[
  {
    "flight_id": 1001,
    "flightno": "AA123",
    "airline": "American Airlines",
    "departure_airport": "John F Kennedy International",
    "arrival_airport": "Los Angeles International",
    "departure": "2025-12-15T08:00:00",
    "arrival": "2025-12-15T11:30:00",
    "duration_minutes": 330,
    "available_seats": 45
  },
  {
    "flight_id": 1002,
    "flightno": "DL456",
    "airline": "Delta Air Lines",
    "departure_airport": "John F Kennedy International",
    "arrival_airport": "Los Angeles International",
    "departure": "2025-12-15T14:15:00",
    "arrival": "2025-12-15T17:45:00",
    "duration_minutes": 330,
    "available_seats": 23
  }
]' EX 300

# Cache popular routes for faster autocomplete
127.0.0.1:6379> ZADD popular:routes 1500 "JFK:LAX" 1200 "LAX:JFK" 1100 "JFK:LHR" 1000 "LAX:NRT"

# Get most popular routes
127.0.0.1:6379> ZREVRANGE popular:routes 0 4 WITHSCORES
```

### Step 13: Round-Trip Flight Search

For round-trip searches, we need to cache both directions:

```sql
-- Round-trip flight search (even more expensive)
-- Outbound flights
SELECT 
    'outbound' as direction,
    f.flight_id,
    f.flightno,
    al.name as airline_name,
    f.departure,
    f.arrival,
    TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as duration_minutes
FROM flight f
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airline al ON f.airline_id = al.airline_id
WHERE dep_a.iata = 'JFK' 
    AND arr_a.iata = 'LAX'
    AND DATE(f.departure) = '2025-12-15'

UNION ALL

-- Return flights
SELECT 
    'return' as direction,
    f.flight_id,
    f.flightno,
    al.name as airline_name,
    f.departure,
    f.arrival,
    TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as duration_minutes
FROM flight f
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airline al ON f.airline_id = al.airline_id
WHERE dep_a.iata = 'LAX' 
    AND arr_a.iata = 'JFK'
    AND DATE(f.departure) = '2025-12-22'
ORDER BY direction, departure;
```

**Cache round-trip results:**
```bash
# Cache round-trip search with compound key
127.0.0.1:6379> SET flight:roundtrip:JFK:LAX:2025-12-15:2025-12-22 '{
  "outbound": [
    {"flight_id": 1001, "flightno": "AA123", "departure": "2025-12-15T08:00:00", "arrival": "2025-12-15T11:30:00"},
    {"flight_id": 1002, "flightno": "DL456", "departure": "2025-12-15T14:15:00", "arrival": "2025-12-15T17:45:00"}
  ],
  "return": [
    {"flight_id": 2001, "flightno": "AA124", "departure": "2025-12-22T09:00:00", "arrival": "2025-12-22T17:30:00"},
    {"flight_id": 2002, "flightno": "DL457", "departure": "2025-12-22T15:30:00", "arrival": "2025-12-22T23:45:00"}
  ]
}' EX 600

# Monitor cache usage
127.0.0.1:6379> GET flight:roundtrip:JFK:LAX:2025-12-15:2025-12-22
```

### Step 14: User Profile - Last 10 Flights

This is another critical user-facing query that benefits greatly from caching:

```sql
-- Get user's last 10 flights with full details (expensive query)
SELECT 
    b.booking_id,
    f.flightno,
    al.name as airline_name,
    al.iata as airline_code,
    dep_a.name as departure_airport,
    dep_a.iata as dep_iata,
    dep_ag.city as dep_city,
    dep_ag.country as dep_country,
    arr_a.name as arrival_airport,
    arr_a.iata as arr_iata,
    arr_ag.city as arr_city,
    arr_ag.country as arr_country,
    f.departure,
    f.arrival,
    b.seat,
    b.price,
    CASE 
        WHEN f.departure > NOW() THEN 'upcoming'
        WHEN f.arrival < NOW() THEN 'completed'
        ELSE 'in_progress'
    END as flight_status
FROM booking b
JOIN flight f ON b.flight_id = f.flight_id
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport_geo dep_ag ON dep_a.airport_id = dep_ag.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airport_geo arr_ag ON arr_a.airport_id = arr_ag.airport_id
JOIN airline al ON f.airline_id = al.airline_id
WHERE b.passenger_id = 12345  -- User's passenger ID
ORDER BY f.departure DESC
LIMIT 10;
```

**Analyze this query:**
```sql
EXPLAIN SELECT 
    b.booking_id,
    f.flightno,
    al.name as airline_name,
    dep_a.name as departure_airport,
    arr_a.name as arrival_airport,
    f.departure,
    f.arrival,
    b.seat,
    b.price
FROM booking b
JOIN flight f ON b.flight_id = f.flight_id
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airline al ON f.airline_id = al.airline_id
WHERE b.passenger_id = 12345
ORDER BY f.departure DESC
LIMIT 10;
```

**Expected Analysis:**
- 5 table joins
- Multiple geographic lookups
- Date comparisons and CASE statements
- ORDER BY with LIMIT
- **Extremely expensive** for frequent profile views!

### Step 15: Cache User Flight History

Implement user-specific caching:

```bash
# Cache user's flight history
127.0.0.1:6379> SET user:12345:flights '[
  {
    "booking_id": 5001,
    "flightno": "AA123",
    "airline": "American Airlines",
    "route": "JFK → LAX",
    "departure_airport": "John F Kennedy International",
    "departure_city": "New York",
    "departure_country": "USA",
    "arrival_airport": "Los Angeles International", 
    "arrival_city": "Los Angeles",
    "arrival_country": "USA",
    "departure": "2025-11-15T08:00:00",
    "arrival": "2025-11-15T11:30:00",
    "seat": "12A",
    "price": 450.00,
    "status": "completed"
  },
  {
    "booking_id": 5002,
    "flightno": "DL789",
    "airline": "Delta Air Lines",
    "route": "LAX → JFK",
    "departure_airport": "Los Angeles International",
    "departure_city": "Los Angeles", 
    "departure_country": "USA",
    "arrival_airport": "John F Kennedy International",
    "arrival_city": "New York",
    "arrival_country": "USA",
    "departure": "2025-12-20T14:15:00",
    "arrival": "2025-12-20T22:45:00",
    "seat": "8C",
    "price": 520.00,
    "status": "upcoming"
  }
]' EX 1800

# Cache user profile summary
127.0.0.1:6379> HSET user:12345:profile total_flights "25" miles_flown "125000" favorite_airline "American Airlines" status "Gold"

# Cache user's frequent routes
127.0.0.1:6379> ZADD user:12345:routes 8 "JFK:LAX" 6 "LAX:JFK" 4 "JFK:LHR" 3 "LHR:JFK"
```

### Step 16: Real-Time Seat Availability Caching

One of the most critical aspects of flight booking is real-time seat availability:

```mermaid
graph TB
    subgraph "Seat Availability System"
        A[Flight 1001<br/>150 Total Seats] --> B{Cache Check}
        B -->|Hit| C[Return Availability<br/>~0.1ms]
        B -->|Miss| D[Database Query<br/>~50-150ms]
        
        D --> E[Count Bookings]
        E --> F[Calculate Available]
        F --> G[Update Cache]
        G --> C
    end
    
    subgraph "Real-Time Updates"
        H[New Booking] --> I[Atomic Update]
        I --> J[Update Seat Bitmap]
        I --> K[Update Counters]
        I --> L[Invalidate Search Cache]
    end
    
    subgraph "Data Structures"
        M[Hash: flight:1001:seats<br/>total_seats: 150<br/>booked_seats: 45<br/>available_seats: 105]
        N[Bitmap: flight:1001:seatmap<br/>Bit 0: Seat 1A<br/>Bit 1: Seat 1B<br/>...]
    end
    
    style A fill:#e3f2fd
    style C fill:#e8f5e8
    style H fill:#fff3e0
    style I fill:#ffecb3
```

```sql
-- Check seat availability for a specific flight (frequent query)
SELECT 
    f.flight_id,
    f.flightno,
    COUNT(b.booking_id) as booked_seats,
    (150 - COUNT(b.booking_id)) as available_seats,  -- Assuming 150 seat aircraft
    GROUP_CONCAT(b.seat ORDER BY b.seat) as booked_seat_numbers
FROM flight f
LEFT JOIN booking b ON f.flight_id = b.flight_id
WHERE f.flight_id = 1001
GROUP BY f.flight_id, f.flightno;
```

**Cache seat availability with atomic updates:**
```bash
# Initialize seat availability for flight
127.0.0.1:6379> HSET flight:1001:seats total_seats 150 booked_seats 0 available_seats 150

# Cache specific seat map (using bitmap for efficiency)
127.0.0.1:6379> SETBIT flight:1001:seatmap 0 0   # Seat 1A available (0)
127.0.0.1:6379> SETBIT flight:1001:seatmap 1 1   # Seat 1B booked (1)
127.0.0.1:6379> SETBIT flight:1001:seatmap 2 0   # Seat 1C available (0)

# When a seat is booked, update atomically
127.0.0.1:6379> MULTI
127.0.0.1:6379> SETBIT flight:1001:seatmap 0 1   # Book seat 1A
127.0.0.1:6379> HINCRBY flight:1001:seats booked_seats 1
127.0.0.1:6379> HINCRBY flight:1001:seats available_seats -1
127.0.0.1:6379> EXEC

# Check seat availability quickly
127.0.0.1:6379> HGET flight:1001:seats available_seats
127.0.0.1:6379> GETBIT flight:1001:seatmap 0  # Check if seat 1A is available
```

### Step 17: Smart Cache Invalidation for User Data

When a user books a new flight, we need to invalidate their cached data:

```mermaid
graph TB
    subgraph "Cache Invalidation Flow"
        A[User Books Flight] --> B[Booking Event]
        B --> C{Identify Affected Caches}
        
        C --> D[User Profile Cache]
        C --> E[Flight Search Cache]
        C --> F[Seat Availability Cache]
        C --> G[Route Statistics Cache]
        
        D --> H[DEL user:12345:flights]
        E --> I[DEL flight:search:JFK:LAX:*]
        F --> J[Update flight:1001:seats]
        G --> K[ZINCRBY user:12345:routes]
    end
    
    subgraph "Cache Tags System"
        L[Cache Tags] --> M[user:12345 → user caches]
        L --> N[flight:1001 → flight caches]
        L --> O[route:JFK:LAX → search caches]
    end
    
    subgraph "Invalidation Strategies"
        P[Immediate<br/>Critical Data] --> Q[User Profile<br/>Seat Availability]
        R[Lazy<br/>Non-Critical] --> S[Statistics<br/>Analytics]
        T[Time-Based<br/>TTL Expiry] --> U[Search Results<br/>Route Data]
    end
    
    style A fill:#e3f2fd
    style B fill:#fff3e0
    style P fill:#ffcdd2
    style R fill:#f3e5f5
    style T fill:#e8f5e8
```

```bash
# When user books a new flight, invalidate related caches
127.0.0.1:6379> DEL user:12345:flights
127.0.0.1:6379> HINCRBY user:12345:profile total_flights 1
127.0.0.1:6379> ZINCRBY user:12345:routes 1 "JFK:LAX"

# Set up cache tags for complex invalidation
127.0.0.1:6379> SADD cache:tags:user:12345 "user:12345:flights" "user:12345:profile"
127.0.0.1:6379> SADD cache:tags:flight:1001 "flight:search:JFK:LAX:2025-12-15"

# When flight 1001 is cancelled, invalidate all related searches
127.0.0.1:6379> SMEMBERS cache:tags:flight:1001
127.0.0.1:6379> DEL flight:search:JFK:LAX:2025-12-15

# Invalidate seat availability when booking occurs
127.0.0.1:6379> DEL flight:1001:seats
127.0.0.1:6379> DEL flight:1001:seatmap
```

### Step 18: Cache Performance for User-Facing Queries

Let's measure the performance impact of caching these critical queries:

**Flight Search Performance:**
```bash
# Simulate cache miss - measure database query time
time mysql -u flughafen_user -p flughafendb -e "
SELECT f.flight_id, f.flightno, f.departure, f.arrival 
FROM flight f 
JOIN airport dep_a ON f.from_airport = dep_a.airport_id 
JOIN airport arr_a ON f.to_airport = arr_a.airport_id 
WHERE dep_a.iata = 'JFK' AND arr_a.iata = 'LAX' 
AND DATE(f.departure) = '2025-12-15';"

# Simulate cache hit - measure cache retrieval time
time valkey-cli GET flight:search:JFK:LAX:2025-12-15
```

**User Profile Performance:**
```bash
# Database query time for user flights
time mysql -u flughafen_user -p flughafendb -e "
SELECT b.booking_id, f.flightno, f.departure, f.arrival 
FROM booking b 
JOIN flight f ON b.flight_id = f.flight_id 
WHERE b.passenger_id = 12345 
ORDER BY f.departure DESC LIMIT 10;"

# Cache retrieval time
time valkey-cli GET user:12345:flights
```

**Expected Results:**
- Database queries: 50-500ms depending on data size
- Cache hits: 0.1-2ms
- **Performance improvement: 25-500x faster!**

### Step 19: Cache Warming Strategies

For user-facing queries, we need proactive cache warming:

**Popular Route Cache Warming:**
```bash
# Pre-populate cache for popular routes during off-peak hours
127.0.0.1:6379> SET flight:search:JFK:LAX:2025-12-15 "$(mysql -u flughafen_user -p flughafendb -e 'SELECT JSON_ARRAYAGG(JSON_OBJECT("flight_id", f.flight_id, "flightno", f.flightno, "departure", f.departure, "arrival", f.arrival)) FROM flight f JOIN airport dep_a ON f.from_airport = dep_a.airport_id JOIN airport arr_a ON f.to_airport = arr_a.airport_id WHERE dep_a.iata = "JFK" AND arr_a.iata = "LAX" AND DATE(f.departure) = "2025-12-15";')" EX 3600

# Warm cache for next 7 days of popular routes
for date in {15..21}; do
  127.0.0.1:6379> SET flight:search:JFK:LAX:2025-12-$date "flight_data_for_date" EX 3600
done
```

**User Profile Pre-loading:**
```bash
# Pre-load frequent users' flight history
127.0.0.1:6379> SET user:12345:flights "user_flight_history_json" EX 1800
127.0.0.1:6379> SET user:67890:flights "user_flight_history_json" EX 1800

# Use a background job to refresh user caches
127.0.0.1:6379> LPUSH cache:refresh:queue "user:12345:flights" "user:67890:flights"
```

---

## Part 4: Advanced Caching Scenarios

### Step 20: Business Intelligence Queries

Let's work with analytical queries that support business decisions:

```mermaid
graph TB
    subgraph "Business Intelligence Architecture"
        A[BI Dashboard Request] --> B{Check Analytics Cache}
        B -->|Hit| C[Return Cached Report<br/>~1-5ms]
        B -->|Miss| D[Complex Analytics Query]
        
        D --> E[Multi-Table Joins<br/>Routes + Airports + Airlines]
        E --> F[Aggregations<br/>COUNT, GROUP BY]
        F --> G[Sorting & Filtering<br/>Hub Analysis]
        G --> H[Results ~500-2000ms]
        
        H --> I[Cache with Long TTL<br/>1-24 hours]
        I --> C
    end
    
    subgraph "Query Complexity Levels"
        J[Simple Lookups<br/>~1-10ms<br/>Cache: Optional]
        K[Complex Joins<br/>~50-200ms<br/>Cache: Recommended]
        L[Analytics Queries<br/>~500-2000ms<br/>Cache: Essential]
    end
    
    subgraph "Cache Strategy by Query Type"
        M[Real-time Data<br/>TTL: 1-5 min]
        N[Business Reports<br/>TTL: 1-4 hours]
        O[Historical Analysis<br/>TTL: 12-24 hours]
    end
    
    style A fill:#e3f2fd
    style C fill:#e8f5e8
    style D fill:#ffecb3
    style H fill:#ffcdd2
```

Let's work with a more complex, expensive query:

```sql
-- Find all routes from major hub airports (expensive query)
SELECT 
    dep_a.name as departure_airport,
    dep_a.iata as dep_iata,
    arr_a.name as arrival_airport,
    arr_a.iata as arr_iata,
    COUNT(r.route_id) as route_count
FROM route r
JOIN airport dep_a ON r.source_airport_id_openflights = dep_a.openflights_id
JOIN airport arr_a ON r.destination_airport_id_openflights = arr_a.openflights_id
WHERE dep_a.iata IN ('ATL', 'ORD', 'JFK', 'LAX', 'DFW')
GROUP BY dep_a.airport_id, dep_a.name, dep_a.iata, arr_a.airport_id, arr_a.name, arr_a.iata
ORDER BY route_count DESC
LIMIT 20;
```

**Analyze the query cost:**
```sql
EXPLAIN SELECT 
    dep_a.name as departure_airport,
    dep_a.iata as dep_iata,
    arr_a.name as arrival_airport,
    arr_a.iata as arr_iata,
    COUNT(r.route_id) as route_count
FROM route r
JOIN airport dep_a ON r.source_airport_id_openflights = dep_a.openflights_id
JOIN airport arr_a ON r.destination_airport_id_openflights = arr_a.openflights_id
WHERE dep_a.iata IN ('ATL', 'ORD', 'JFK', 'LAX', 'DFW')
GROUP BY dep_a.airport_id, dep_a.name, dep_a.iata, arr_a.airport_id, arr_a.name, arr_a.iata
ORDER BY route_count DESC
LIMIT 20;
```

**Expected Analysis:**
- Multiple table joins
- GROUP BY operation
- ORDER BY with aggregation
- High cost - perfect candidate for caching!

### Step 12: Implement Hierarchical Caching

Let's implement a more sophisticated caching strategy:

```mermaid
graph TB
    subgraph "Hierarchical Cache Structure"
        A[Individual Airport Data<br/>airport:ATL] --> B[Route Summaries<br/>route:ATL:summary]
        B --> C[Hub Statistics<br/>hub:routes:outbound]
        C --> D[Global Analytics<br/>analytics:hub:rankings]
    end
    
    subgraph "Cache Levels & TTL"
        E[Level 1: Raw Data<br/>TTL: 1-6 hours<br/>High Frequency Access]
        F[Level 2: Aggregated<br/>TTL: 6-24 hours<br/>Medium Frequency]
        G[Level 3: Analytics<br/>TTL: 24-72 hours<br/>Low Frequency]
    end
    
    subgraph "Data Flow"
        H[Database] --> I[Level 1 Cache]
        I --> J[Compute Level 2]
        J --> K[Level 2 Cache]
        K --> L[Compute Level 3]
        L --> M[Level 3 Cache]
    end
    
    A -.-> E
    B -.-> F
    C -.-> G
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
```

```bash
# Cache individual airport data
127.0.0.1:6379> HSET airport:ATL name "Hartsfield Jackson Atlanta International Airport"
127.0.0.1:6379> HSET airport:ATL iata "ATL"
127.0.0.1:6379> HSET airport:ATL icao "KATL"
127.0.0.1:6379> HSET airport:ATL city "Atlanta"
127.0.0.1:6379> HSET airport:ATL country "USA"

# Cache route counts for major hubs
127.0.0.1:6379> ZADD hub:routes:outbound 1000 "ATL" 800 "ORD" 750 "JFK" 700 "LAX" 650 "DFW"

# Get top hubs by route count
127.0.0.1:6379> ZREVRANGE hub:routes:outbound 0 4 WITHSCORES
1) "ATL"
2) "1000"
3) "ORD"
4) "800"
5) "JFK"
6) "750"
7) "LAX"
8) "700"
9) "DFW"
10) "650"
```

### Step 13: Cache Invalidation Strategy

Let's implement a cache invalidation pattern:

```bash
# Set up cache with tags for invalidation
127.0.0.1:6379> SET route:ATL:summary '{"total_routes":1000,"destinations":250,"airlines":45}' EX 3600
127.0.0.1:6379> SADD cache:tags:airport:ATL "route:ATL:summary"
127.0.0.1:6379> SADD cache:tags:routes "route:ATL:summary"

# When airport data changes, invalidate related caches
127.0.0.1:6379> SMEMBERS cache:tags:airport:ATL
1) "route:ATL:summary"

# Delete all caches tagged with airport:ATL
127.0.0.1:6379> DEL route:ATL:summary
127.0.0.1:6379> DEL cache:tags:airport:ATL
```

### Step 14: Monitor Cache Performance

Let's monitor cache hit rates and performance:

```bash
# Get cache statistics
127.0.0.1:6379> INFO stats

# Key metrics to watch:
# - keyspace_hits: Number of successful lookups
# - keyspace_misses: Number of failed lookups
# - hit_rate = hits / (hits + misses)

# Monitor memory usage
127.0.0.1:6379> INFO memory

# Check specific key information
127.0.0.1:6379> MEMORY USAGE airport:ATL
127.0.0.1:6379> OBJECT ENCODING airport:ATL
```

### Step 15: Advanced Cache Patterns

```mermaid
graph TB
    subgraph "Write-Through Pattern"
        A[Application Update] --> B[Update Database]
        A --> C[Update Cache]
        B --> D[Data Consistency]
        C --> D
    end
    
    subgraph "Write-Behind Pattern"
        E[Application Update] --> F[Update Cache]
        F --> G[Async Update DB]
        G --> H[Higher Performance]
    end
    
    subgraph "Cache-Aside Pattern"
        I[Read Request] --> J{Cache Hit?}
        J -->|Yes| K[Return Cached Data]
        J -->|No| L[Read from DB]
        L --> M[Update Cache]
        M --> K
    end
    
    subgraph "TTL Strategy"
        N[Static Data<br/>TTL: 24h] --> O[Airport Names<br/>Country Codes]
        P[Semi-Static<br/>TTL: 1-6h] --> Q[Flight Schedules<br/>Route Info]
        R[Dynamic Data<br/>TTL: 1-15min] --> S[Seat Availability<br/>Search Results]
        T[Real-time<br/>TTL: 30s-2min] --> U[Live Prices<br/>Booking Status]
    end
    
    style A fill:#e3f2fd
    style E fill:#f3e5f5
    style I fill:#e8f5e8
    style N fill:#fff3e0
```

**Write-Through Pattern:**
```bash
# When updating airport data, update both database and cache
# 1. Update database (in SQL terminal)
UPDATE airport SET name = 'Updated Airport Name' WHERE iata = 'ATL';

# 2. Update cache immediately (in Valkey terminal)
127.0.0.1:6379> HSET airport:ATL name "Updated Airport Name"
```

**Cache Warming:**
```bash
# Pre-populate cache with frequently accessed data
127.0.0.1:6379> MSET airport:JFK:name "John F Kennedy International" airport:LAX:name "Los Angeles International" airport:ORD:name "Chicago O'Hare International"
```

**TTL Management:**
```bash
# Set different TTLs based on data volatility
127.0.0.1:6379> EXPIRE airport:ATL:static_data 86400    # 24 hours for static data
127.0.0.1:6379> EXPIRE airport:ATL:flight_count 300     # 5 minutes for dynamic data
```

## Part 4: Real-World Scenarios

### Step 16: Session Management Caching

Simulate user session caching:

```bash
# Store user session data
127.0.0.1:6379> HSET session:user123 user_id "123"
127.0.0.1:6379> HSET session:user123 username "pilot_john"
127.0.0.1:6379> HSET session:user123 last_airport "JFK"
127.0.0.1:6379> HSET session:user123 preferences '{"theme":"dark","language":"en"}'
127.0.0.1:6379> EXPIRE session:user123 1800  # 30-minute session timeout

# Retrieve session data
127.0.0.1:6379> HGETALL session:user123
```

### Step 17: Leaderboard Implementation

Create a real-time airport traffic leaderboard:

```mermaid
graph TB
    subgraph "Leaderboard Architecture"
        A[Airport Traffic Data] --> B[Sorted Set<br/>ZADD airport:traffic:daily]
        B --> C[Real-time Updates<br/>ZINCRBY operations]
        C --> D[Leaderboard Queries<br/>ZREVRANGE with scores]
    end
    
    subgraph "Leaderboard Operations"
        E[Add/Update Score<br/>ZADD key score member] --> F[Increment Score<br/>ZINCRBY key increment member]
        F --> G[Get Top N<br/>ZREVRANGE key 0 N WITHSCORES]
        G --> H[Get Rank<br/>ZREVRANK key member]
    end
    
    subgraph "Use Cases"
        I[Busiest Airports<br/>Daily/Monthly Traffic]
        J[Popular Routes<br/>Booking Frequency]
        K[Top Airlines<br/>Flight Volume]
        L[User Rankings<br/>Miles Flown]
    end
    
    subgraph "Performance Benefits"
        M[O(log N) Updates<br/>Very Fast Inserts]
        N[O(log N + M) Range Queries<br/>Efficient Top-K]
        O[Real-time Rankings<br/>Live Leaderboards]
    end
    
    style A fill:#e3f2fd
    style C fill:#e8f5e8
    style G fill:#f3e5f5
    style M fill:#fff3e0
```

```bash
# Add airports to leaderboard with passenger counts
127.0.0.1:6379> ZADD airport:traffic:daily 95000000 "ATL" 87000000 "PEK" 83000000 "DXB" 79000000 "LAX" 78000000 "ORD"

# Get top 5 busiest airports
127.0.0.1:6379> ZREVRANGE airport:traffic:daily 0 4 WITHSCORES

# Update traffic count (simulate real-time updates)
127.0.0.1:6379> ZINCRBY airport:traffic:daily 1000 "JFK"

# Get airport rank
127.0.0.1:6379> ZREVRANK airport:traffic:daily "JFK"
```

### Step 18: Cache Stampede Prevention

Simulate and prevent cache stampede:

```mermaid
sequenceDiagram
    participant A1 as App Instance 1
    participant A2 as App Instance 2
    participant A3 as App Instance 3
    participant C as Cache
    participant DB as Database
    
    Note over A1,DB: Cache Stampede Scenario
    
    A1->>C: GET expensive:query:result
    A2->>C: GET expensive:query:result  
    A3->>C: GET expensive:query:result
    C-->>A1: (nil) - Cache Miss
    C-->>A2: (nil) - Cache Miss
    C-->>A3: (nil) - Cache Miss
    
    Note over A1,DB: Without Protection - All Query DB
    
    A1->>DB: Expensive Query (500ms)
    A2->>DB: Expensive Query (500ms)
    A3->>DB: Expensive Query (500ms)
    
    Note over A1,DB: With Lock Protection
    
    A1->>C: SET cache:lock:expensive_query "locked" EX 60 NX
    A2->>C: SET cache:lock:expensive_query "locked" EX 60 NX
    A3->>C: SET cache:lock:expensive_query "locked" EX 60 NX
    C-->>A1: OK (Lock Acquired)
    C-->>A2: (nil) - Lock Failed
    C-->>A3: (nil) - Lock Failed
    
    A1->>DB: Expensive Query (500ms)
    A2->>A2: Wait & Retry
    A3->>A3: Wait & Retry
    
    DB-->>A1: Query Results
    A1->>C: SET expensive:query:result [data] EX 3600
    A1->>C: DEL cache:lock:expensive_query
    
    A2->>C: GET expensive:query:result
    A3->>C: GET expensive:query:result
    C-->>A2: [cached data] - Cache Hit
    C-->>A3: [cached data] - Cache Hit
```

```bash
# Set a lock to prevent multiple processes from rebuilding cache simultaneously
127.0.0.1:6379> SET cache:lock:expensive_query "locked" EX 60 NX
OK

# If lock acquired, rebuild cache
127.0.0.1:6379> SET expensive:query:result "rebuilt_data" EX 3600

# Release lock
127.0.0.1:6379> DEL cache:lock:expensive_query

# If lock not acquired (returns nil), wait and retry
127.0.0.1:6379> SET cache:lock:expensive_query "locked" EX 60 NX
(nil)
```

## Part 5: Performance Analysis and Optimization

### Step 19: Comprehensive Performance Testing

**Database Query Performance:**
```sql
-- Time expensive queries
SET profiling = 1;

SELECT 
    ag.country,
    COUNT(*) as airport_count,
    AVG(ag.altitude) as avg_altitude
FROM airport_geo ag
WHERE ag.country IS NOT NULL
GROUP BY ag.country
ORDER BY airport_count DESC
LIMIT 10;

SHOW PROFILES;
```

**Cache Performance Testing:**
```bash
# Test cache performance with multiple operations
127.0.0.1:6379> EVAL "
local start_time = redis.call('TIME')
for i=1,1000 do
    redis.call('GET', 'test:key:' .. i)
end
local end_time = redis.call('TIME')
return {start_time, end_time}
" 0
```

### Step 20: Memory Optimization

```bash
# Analyze memory usage patterns
127.0.0.1:6379> MEMORY DOCTOR

# Use efficient data structures
127.0.0.1:6379> HSET airport:compact:JFK n "John F Kennedy International" i "JFK" c "KJFK" ct "New York"

# Compare with verbose version
127.0.0.1:6379> MEMORY USAGE airport:compact:JFK
127.0.0.1:6379> MEMORY USAGE airport:JFK:details
```

### Step 21: Cache Eviction Policies

```bash
# Check current eviction policy
127.0.0.1:6379> CONFIG GET maxmemory-policy

# Set eviction policy for workshop
127.0.0.1:6379> CONFIG SET maxmemory-policy allkeys-lru

# Monitor evictions
127.0.0.1:6379> INFO stats | grep evicted
```

## Part 6: Monitoring and Observability

### Step 22: Set Up Monitoring

**Real-time Monitoring:**
```bash
# Monitor commands in real-time (keep this running)
valkey-cli --latency-history -i 1

# In another terminal, monitor memory usage
watch -n 1 'valkey-cli INFO memory | grep used_memory_human'
```

**Performance Metrics:**
```bash
# Get comprehensive stats
127.0.0.1:6379> INFO all

# Key metrics to monitor:
# - instantaneous_ops_per_sec: Current operations per second
# - used_memory_human: Memory usage
# - keyspace_hits/keyspace_misses: Hit rate
# - expired_keys: Keys expired
# - evicted_keys: Keys evicted due to memory pressure
```

### Step 23: Alerting Thresholds

```bash
# Set up basic alerting logic
127.0.0.1:6379> EVAL "
local memory_usage = redis.call('INFO', 'memory')
local used_memory = string.match(memory_usage, 'used_memory:(%d+)')
local max_memory = redis.call('CONFIG', 'GET', 'maxmemory')[2]

if tonumber(used_memory) > tonumber(max_memory) * 0.8 then
    return 'ALERT: Memory usage above 80%'
else
    return 'Memory usage OK'
end
" 0
```

## Workshop Summary and Key Takeaways

```mermaid
graph TB
    subgraph "Performance Improvements"
        A[Database Only<br/>50-500ms] --> B[With Caching<br/>0.1-2ms]
        B --> C[75-5000x<br/>Improvement]
    end
    
    subgraph "Query Performance by Type"
        D[Flight Search<br/>500ms → 2ms<br/>250x faster]
        E[User History<br/>800ms → 1ms<br/>800x faster]
        F[Seat Check<br/>150ms → 0.5ms<br/>300x faster]
        G[BI Queries<br/>2000ms → 5ms<br/>400x faster]
    end
    
    subgraph "Cache Hit Rate Targets"
        H[Flight Searches<br/>>95% hit rate]
        I[User Profiles<br/>>90% hit rate]
        J[Seat Availability<br/>>85% hit rate]
        K[Analytics<br/>>80% hit rate]
    end
    
    subgraph "Memory Efficiency"
        L[JSON Strings<br/>Flexible, Higher Memory]
        M[Hash Structures<br/>Structured, Lower Memory]
        N[Bitmaps<br/>Seat Maps, Minimal Memory]
        O[Compressed<br/>Lowest Memory, CPU Cost]
    end
    
    style C fill:#e8f5e8
    style D fill:#e3f2fd
    style H fill:#f3e5f5
    style L fill:#fff3e0
```

### Performance Improvements Observed

1. **User-Facing Query Performance:**
   - **Flight Search (JFK→LAX)**: 150-500ms → 0.5-2ms (75-1000x improvement)
   - **User Flight History**: 200-800ms → 0.2-1ms (200-4000x improvement)
   - **Seat Availability Check**: 50-150ms → 0.1-0.5ms (100-1500x improvement)
   - **Round-trip Search**: 300-1000ms → 1-3ms (300-1000x improvement)

2. **Database Query Optimization:**
   - Simple indexed queries (IATA lookup): ~1ms
   - Complex joins without cache: ~50-200ms
   - Same queries with cache: ~0.1-1ms

3. **Cache Hit Rates by Query Type:**
   - Flight searches: Target >95% (high repeatability)
   - User profiles: Target >90% (frequent access)
   - Seat availability: Target >85% (real-time updates)
   - Route analysis: Target >80% (business intelligence)

4. **Memory Efficiency:**
   - JSON strings: Higher memory usage but flexible
   - Hash structures: Lower memory, structured access
   - Bitmap for seat maps: Extremely memory efficient
   - Compressed formats: Lowest memory, processing overhead

### Best Practices Learned

```mermaid
graph TB
    subgraph "Cache Key Design Patterns"
        A[Hierarchical Keys<br/>service:entity:identifier]
        B[flight:search:JFK:LAX:2025-12-15]
        C[user:12345:flights]
        D[flight:1001:seats]
        A --> B
        A --> C
        A --> D
    end
    
    subgraph "TTL Strategy Matrix"
        E[Data Volatility] --> F[TTL Duration]
        F --> G[Static Data: 24h<br/>Airport names, countries]
        F --> H[Semi-Static: 1-6h<br/>Flight schedules, routes]
        F --> I[Dynamic: 5-15min<br/>Search results, prices]
        F --> J[Real-time: 30s-2min<br/>Seat availability, bookings]
    end
    
    subgraph "Invalidation Strategies"
        K[Event-Driven<br/>Immediate] --> L[User bookings<br/>Profile updates]
        M[Time-Based<br/>TTL Expiry] --> N[Search results<br/>Analytics]
        O[Manual<br/>Admin Actions] --> P[System maintenance<br/>Data corrections]
    end
    
    subgraph "Monitoring Metrics"
        Q[Hit Rate %<br/>Target: >90%]
        R[Response Time<br/>Target: <2ms]
        S[Memory Usage<br/>Monitor growth]
        T[Eviction Rate<br/>Optimize TTL]
    end
    
    style A fill:#e3f2fd
    style E fill:#f3e5f5
    style K fill:#e8f5e8
    style Q fill:#fff3e0
```

1. **Cache Key Design for User-Facing Queries:**
   - **Flight searches**: `flight:search:{origin}:{destination}:{date}`
   - **User profiles**: `user:{user_id}:{data_type}`
   - **Seat availability**: `flight:{flight_id}:seats` and `flight:{flight_id}:seatmap`
   - Include version/namespace information for schema changes

2. **TTL Strategy by Query Type:**
   - **Flight searches**: 5-15 minutes (balance freshness vs performance)
   - **User flight history**: 30 minutes (updated on new bookings)
   - **Seat availability**: 1-2 minutes (critical for booking accuracy)
   - **Route analysis**: 1-24 hours (business intelligence, less critical)

3. **Cache Invalidation Patterns:**
   - **Booking events**: Invalidate user profiles and seat availability
   - **Flight changes**: Invalidate all related search results
   - **Schedule updates**: Invalidate route and flight data
   - **User actions**: Immediate invalidation of user-specific caches

4. **Performance Monitoring for User Experience:**
   - Track response times for critical user journeys
   - Monitor cache hit rates for flight searches (target >95%)
   - Alert on seat availability cache misses (booking failures)
   - Measure user session performance improvements

### Business Impact of Caching

```mermaid
graph TB
    subgraph "User Experience Impact"
        A[Slow Responses<br/>500ms+] --> B[User Frustration<br/>High Abandonment]
        C[Fast Responses<br/><2ms] --> D[Smooth Experience<br/>Higher Conversion]
        
        E[Mobile Users<br/>Slow Networks] --> F[Critical Performance<br/>Caching Essential]
    end
    
    subgraph "System Scalability"
        G[Database Load<br/>100% queries] --> H[With Cache<br/>10-30% queries]
        H --> I[10-50x More Users<br/>Same Infrastructure]
        
        J[Peak Traffic<br/>Holiday Rushes] --> K[Cache Absorbs<br/>Traffic Spikes]
    end
    
    subgraph "Revenue Impact"
        L[Faster Search<br/>2ms response] --> M[Higher Conversion<br/>+15-30%]
        N[Better UX] --> O[User Retention<br/>Repeat Customers]
        P[System Reliability] --> Q[Reduced Support<br/>Lower Costs]
        R[Performance Edge] --> S[Competitive Advantage<br/>Market Share]
    end
    
    subgraph "Cost Savings"
        T[Database Servers<br/>Reduced Load] --> U[Infrastructure Savings<br/>30-70% reduction]
        V[Support Tickets<br/>Fewer Issues] --> W[Operational Savings<br/>Staff efficiency]
    end
    
    style D fill:#e8f5e8
    style I fill:#e3f2fd
    style M fill:#f3e5f5
    style U fill:#fff3e0
```

1. **User Experience Improvements:**
   - **Flight search response time**: 500ms → 2ms (perceived as instant)
   - **Profile page load time**: 800ms → 1ms (seamless experience)
   - **Booking flow speed**: Reduced abandonment due to faster responses
   - **Mobile performance**: Critical for mobile users on slower connections

2. **System Scalability:**
   - **Database load reduction**: 70-90% reduction in expensive queries
   - **Concurrent user capacity**: 10-50x more users with same infrastructure
   - **Peak traffic handling**: Black Friday, holiday booking rushes
   - **Cost savings**: Reduced database server requirements

3. **Revenue Impact:**
   - **Conversion rate improvement**: Faster searches = more bookings
   - **User retention**: Better experience leads to repeat customers
   - **Operational efficiency**: Reduced support tickets from slow systems
   - **Competitive advantage**: Faster than competitors' booking systems

### Next Steps

1. **Implement in Application Code:**
   - Use these patterns in your Python/Node.js/Java applications
   - Implement proper error handling and fallback mechanisms
   - Add comprehensive logging and monitoring

2. **Advanced Patterns:**
   - Implement distributed caching with multiple Valkey instances
   - Explore Valkey Cluster for horizontal scaling
   - Investigate Valkey modules for specialized use cases

3. **Production Considerations:**
   - Set up proper backup and recovery procedures
   - Implement security measures (authentication, encryption)
   - Plan for capacity and scaling requirements

## Troubleshooting Common Issues

### Database Connection Issues
```bash
# Test database connectivity
mysqladmin -u flughafen_user -p ping
# or
pg_isready -U flughafen_user -d flughafendb
```

### Valkey Connection Issues
```bash
# Test Valkey connectivity
valkey-cli ping

# Check Valkey server status
valkey-cli INFO server
```

### Performance Issues
```sql
-- Check for missing indexes
SHOW INDEX FROM airport;
SHOW INDEX FROM airport_geo;

-- Analyze slow queries
SHOW PROCESSLIST;
```

### Cache Issues
```bash
# Clear all cache data
127.0.0.1:6379> FLUSHALL

# Check memory usage
127.0.0.1:6379> INFO memory

# Monitor slow operations
127.0.0.1:6379> SLOWLOG GET 10
```

This comprehensive guide provides hands-on experience with database querying, performance analysis, and caching strategies using real aviation data. Each step builds upon the previous one, demonstrating practical applications of caching patterns in a realistic scenario.