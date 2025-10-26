# Flughafen DB - Query Demo Documentation

This document contains the interactive query demonstrations extracted from the Textual-based query demo application. These queries showcase different complexity levels from simple table queries to complex multi-table joins, following the flight rules for tier cities and routes.

## Overview

The query demos are organized by complexity and demonstrate:
- Basic table queries
- Flight rules implementation (ATL to JFK example)
- Progressive complexity from simple to advanced queries
- Real-world aviation data analysis patterns

## Query Categories

### Basic Queries
Simple single-table operations for getting familiar with the database structure.

### Flight Rules Queries
Queries that implement the flight tier system and routing rules defined in the flight rules documentation.

### Join Queries
Multi-table operations showing relationships between airports, cities, airlines, and geographic data.

### Advanced Queries
Complex analytical queries with multiple joins, aggregations, and business logic.

---

## Demo Queries

### 1. Simple Table Query - Airports
**Complexity:** Beginner  
**Category:** Basic  
**Description:** Basic SELECT from airports table with IATA codes

```sql
SELECT 
    airport_id,
    name,
    iata,
    icao,
    airport_type
FROM airport 
WHERE iata IS NOT NULL 
ORDER BY name 
LIMIT 10
```

This query demonstrates:
- Basic SELECT statement structure
- Column selection
- WHERE clause filtering
- ORDER BY sorting
- LIMIT for result pagination

---

### 2. Tier 1 Hub Airports (Flight Rules)
**Complexity:** Intermediate  
**Category:** Flight Rules  
**Description:** Major hub airports with 500+ routes (ATL, ORD, PEK, LHR, etc.)

```sql
SELECT 
    a.name,
    a.iata,
    a.icao,
    ag.city,
    ag.country,
    COUNT(r.route_id) as route_count
FROM airport a
JOIN airport_geo ag ON a.airport_id = ag.airport_id
LEFT JOIN route r ON a.openflights_id = r.source_airport_id_openflights 
    OR a.openflights_id = r.destination_airport_id_openflights
WHERE a.iata IN ('ATL', 'ORD', 'PEK', 'LHR', 'CDG', 'FRA', 'LAX', 'DFW', 'JFK', 'AMS')
GROUP BY a.airport_id, a.name, a.iata, a.icao, ag.city, ag.country
ORDER BY route_count DESC
```

This query demonstrates:
- INNER JOIN between airport and geographic data
- LEFT JOIN to count routes
- OR conditions in JOIN clauses
- GROUP BY with multiple columns
- COUNT aggregation
- IN clause for filtering specific airports

---

### 3. City-Airport Relationships
**Complexity:** Intermediate  
**Category:** Joins  
**Description:** Join cities with their primary airports using geographic data

```sql
SELECT 
    c.name as city_name,
    c.country_code,
    c.population,
    a.name as airport_name,
    a.iata,
    car.distance_km,
    car.is_primary_airport
FROM city c
JOIN city_airport_relation car ON c.city_id = car.city_id
JOIN airport a ON car.airport_id = a.airport_id
WHERE car.is_primary_airport = true
    AND c.population > 1000000
ORDER BY c.population DESC
LIMIT 15
```

This query demonstrates:
- Multiple INNER JOINs
- Column aliasing for clarity
- Boolean filtering
- Numeric comparisons
- Population-based filtering for major cities

---

### 4. ATL to JFK Route Analysis (Flight Rules Example)
**Complexity:** Advanced  
**Category:** Flight Rules  
**Description:** Tier 1 to Tier 1 route analysis with airline and aircraft data

```sql
SELECT 
    f.flightno,
    al.name as airline_name,
    al.iata as airline_code,
    dep_a.name as departure_airport,
    arr_a.name as arrival_airport,
    f.departure,
    f.arrival,
    TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as flight_duration_minutes
FROM flight f
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id  
JOIN airline al ON f.airline_id = al.airline_id
WHERE dep_a.iata = 'ATL' 
    AND arr_a.iata = 'JFK'
ORDER BY f.departure DESC
LIMIT 10
```

This query demonstrates:
- Multiple table aliases for clarity
- Self-referencing joins (airport table used twice)
- TIMESTAMPDIFF function for duration calculation
- Date/time filtering and sorting
- Real-world flight route analysis

---

### 5. Complex Multi-Table Route Analysis
**Complexity:** Expert  
**Category:** Advanced  
**Description:** Full route analysis with geographic, airline, and city data

```sql
SELECT 
    dep_city.name as departure_city,
    dep_city.population as dep_population,
    dep_ag.country as dep_country,
    arr_city.name as arrival_city, 
    arr_city.population as arr_population,
    arr_ag.country as arr_country,
    al.name as airline_name,
    COUNT(f.flight_id) as flight_count,
    AVG(TIMESTAMPDIFF(MINUTE, f.departure, f.arrival)) as avg_duration_minutes,
    CASE 
        WHEN COUNT(f.flight_id) >= 500 THEN 'Tier 1'
        WHEN COUNT(f.flight_id) >= 200 THEN 'Tier 2' 
        WHEN COUNT(f.flight_id) >= 50 THEN 'Tier 3'
        ELSE 'Tier 4+'
    END as route_tier
FROM flight f
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airport_geo dep_ag ON dep_a.airport_id = dep_ag.airport_id
JOIN airport_geo arr_ag ON arr_a.airport_id = arr_ag.airport_id
JOIN airline al ON f.airline_id = al.airline_id
LEFT JOIN city_airport_relation dep_car ON dep_a.airport_id = dep_car.airport_id AND dep_car.is_primary_airport = true
LEFT JOIN city dep_city ON dep_car.city_id = dep_city.city_id
LEFT JOIN city_airport_relation arr_car ON arr_a.airport_id = arr_car.airport_id AND arr_car.is_primary_airport = true  
LEFT JOIN city arr_city ON arr_car.city_id = arr_city.city_id
WHERE dep_ag.country != arr_ag.country
GROUP BY 
    dep_city.name, dep_city.population, dep_ag.country,
    arr_city.name, arr_city.population, arr_ag.country, 
    al.name
HAVING flight_count >= 10
ORDER BY flight_count DESC, avg_duration_minutes ASC
LIMIT 20
```

This query demonstrates:
- Complex multi-table joins (8 tables)
- Mix of INNER and LEFT JOINs
- CASE statement for tier classification
- Aggregate functions (COUNT, AVG)
- HAVING clause for post-aggregation filtering
- Multiple ORDER BY criteria
- International route filtering (different countries)

---

### 6. Flight Frequency by Distance (Flight Rules)
**Complexity:** Expert  
**Category:** Flight Rules  
**Description:** Analyze flight frequency recommendations based on distance tiers

```sql
SELECT 
    CASE 
        WHEN 6371 * 2 * ASIN(SQRT(
            POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
            COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
            POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
        )) <= 1500 THEN 'Short-haul (0-1,500km)'
        WHEN 6371 * 2 * ASIN(SQRT(
            POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
            COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
            POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
        )) <= 4000 THEN 'Medium-haul (1,500-4,000km)'
        ELSE 'Long-haul (4,000+km)'
    END as distance_category,
    COUNT(DISTINCT CONCAT(dep_a.iata, '-', arr_a.iata)) as unique_routes,
    COUNT(f.flight_id) as total_flights,
    AVG(COUNT(f.flight_id)) OVER (PARTITION BY 
        CASE 
            WHEN 6371 * 2 * ASIN(SQRT(
                POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
                COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
                POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
            )) <= 1500 THEN 'Short-haul'
            WHEN 6371 * 2 * ASIN(SQRT(
                POWER(SIN((RADIANS(arr_ag.latitude) - RADIANS(dep_ag.latitude)) / 2), 2) +
                COS(RADIANS(dep_ag.latitude)) * COS(RADIANS(arr_ag.latitude)) * 
                POWER(SIN((RADIANS(arr_ag.longitude) - RADIANS(dep_ag.longitude)) / 2), 2)
            )) <= 4000 THEN 'Medium-haul'
            ELSE 'Long-haul'
        END
    ) as avg_flights_per_route
FROM flight f
JOIN airport dep_a ON f.from_airport = dep_a.airport_id
JOIN airport arr_a ON f.to_airport = arr_a.airport_id
JOIN airport_geo dep_ag ON dep_a.airport_id = dep_ag.airport_id
JOIN airport_geo arr_ag ON arr_a.airport_id = arr_ag.airport_id
WHERE dep_ag.latitude IS NOT NULL 
    AND dep_ag.longitude IS NOT NULL
    AND arr_ag.latitude IS NOT NULL 
    AND arr_ag.longitude IS NOT NULL
GROUP BY distance_category
ORDER BY 
    CASE distance_category
        WHEN 'Short-haul (0-1,500km)' THEN 1
        WHEN 'Medium-haul (1,500-4,000km)' THEN 2
        ELSE 3
    END
```

This query demonstrates:
- Haversine formula for calculating great-circle distances
- Complex CASE statements with mathematical functions
- Window functions (AVG OVER PARTITION BY)
- DISTINCT COUNT for unique route counting
- String concatenation (CONCAT)
- Mathematical functions (RADIANS, SIN, COS, ASIN, SQRT, POWER)
- Custom ordering with CASE in ORDER BY

---

## Query Execution Features

The interactive demo provides several advanced features:

### SQL Display
- Syntax highlighting for SQL queries
- Real-time query display as you select different demos

### Query Results
- Tabular display of query results
- Automatic formatting for dates, numbers, and text
- Row count and execution timing

### Execution Plan Analysis
- EXPLAIN plan display for query optimization
- Performance analysis capabilities
- Database-agnostic explain plan formatting

### Status Monitoring
- Real-time execution status
- Progress indicators
- Error handling and display

## Usage Instructions

To run the interactive demo:

1. Ensure dependencies are installed: `uv sync`
2. Configure your database connection in `.env`
3. Run the demo: `python scripts/textual_query_demo.py`

The demo provides a terminal-based user interface with:
- Query selection panel on the left
- Tabbed interface for SQL, Results, and Execution Plan
- Real-time status updates and progress indicators

## Flight Rules Integration

Several queries specifically implement the flight rules defined in the system:

- **Tier 1 Airports**: Major hubs with 500+ routes
- **Route Tiers**: Classification based on flight frequency
- **Distance Categories**: Short-haul, medium-haul, and long-haul classifications
- **Hub Analysis**: Focus on major aviation hubs like ATL, JFK, ORD

These queries serve as practical examples of how the flight rules are implemented in SQL and can be used as templates for building similar analytical queries.