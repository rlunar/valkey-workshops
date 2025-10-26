-- Sample queries to find available flights from 5 cities (one for each tier) from last week
-- Based on flight_rules.md tier definitions and database schema

-- Set date range for last week (adjust dates as needed)
SET @last_week_start = DATE_SUB(CURDATE(), INTERVAL 14 DAY);
SET @last_week_end = DATE_SUB(CURDATE(), INTERVAL 7 DAY);

-- ============================================================================
-- TIER 1: Major Hub Airport (500+ routes) - Atlanta (ATL)
-- Expected: Multiple flights per day (6-12 daily flights)
-- ============================================================================

SELECT 
    'TIER 1 - ATL (Major Hub)' as tier,
    f.flight_id,
    f.flightno,
    from_airport.iata as departure_airport,
    from_airport.name as departure_city,
    to_airport.iata as arrival_airport,
    to_airport.name as arrival_city,
    f.departure,
    f.arrival,
    al.iata as airline_code,
    al.airlinename as airline_name,
    ap.capacity as aircraft_capacity
FROM flight f
JOIN airport from_airport ON f.from = from_airport.airport_id
JOIN airport to_airport ON f.to = to_airport.airport_id
JOIN airline al ON f.airline_id = al.airline_id
JOIN airplane ap ON f.airplane_id = ap.airplane_id
WHERE from_airport.iata = 'ATL'
    AND f.departure >= @last_week_start
    AND f.departure <= @last_week_end
ORDER BY f.departure
LIMIT 20;

-- ============================================================================
-- TIER 2: Regional Hub Airport (200-499 routes) - Denver (DEN)
-- Expected: Daily flights (2-6 daily flights)
-- ============================================================================

SELECT 
    'TIER 2 - DEN (Regional Hub)' as tier,
    f.flight_id,
    f.flightno,
    from_airport.iata as departure_airport,
    from_airport.name as departure_city,
    to_airport.iata as arrival_airport,
    to_airport.name as arrival_city,
    f.departure,
    f.arrival,
    al.iata as airline_code,
    al.airlinename as airline_name,
    ap.capacity as aircraft_capacity
FROM flight f
JOIN airport from_airport ON f.from = from_airport.airport_id
JOIN airport to_airport ON f.to = to_airport.airport_id
JOIN airline al ON f.airline_id = al.airline_id
JOIN airplane ap ON f.airplane_id = ap.airplane_id
WHERE from_airport.iata = 'DEN'
    AND f.departure >= @last_week_start
    AND f.departure <= @last_week_end
ORDER BY f.departure
LIMIT 15;

-- ============================================================================
-- TIER 3: Secondary Airport (50-199 routes) - Nashville (BNA)
-- Expected: Daily flights (1-3 daily flights)
-- ============================================================================

SELECT 
    'TIER 3 - BNA (Secondary Airport)' as tier,
    f.flight_id,
    f.flightno,
    from_airport.iata as departure_airport,
    from_airport.name as departure_city,
    to_airport.iata as arrival_airport,
    to_airport.name as arrival_city,
    f.departure,
    f.arrival,
    al.iata as airline_code,
    al.airlinename as airline_name,
    ap.capacity as aircraft_capacity
FROM flight f
JOIN airport from_airport ON f.from = from_airport.airport_id
JOIN airport to_airport ON f.to = to_airport.airport_id
JOIN airline al ON f.airline_id = al.airline_id
JOIN airplane ap ON f.airplane_id = ap.airplane_id
WHERE from_airport.iata = 'BNA'
    AND f.departure >= @last_week_start
    AND f.departure <= @last_week_end
ORDER BY f.departure
LIMIT 10;

-- ============================================================================
-- TIER 4: Regional Airport (10-49 routes) - Boise (BOI)
-- Expected: 3-7 flights per week
-- ============================================================================

SELECT 
    'TIER 4 - BOI (Regional Airport)' as tier,
    f.flight_id,
    f.flightno,
    from_airport.iata as departure_airport,
    from_airport.name as departure_city,
    to_airport.iata as arrival_airport,
    to_airport.name as arrival_city,
    f.departure,
    f.arrival,
    al.iata as airline_code,
    al.airlinename as airline_name,
    ap.capacity as aircraft_capacity,
    DAYNAME(f.departure) as day_of_week
FROM flight f
JOIN airport from_airport ON f.from = from_airport.airport_id
JOIN airport to_airport ON f.to = to_airport.airport_id
JOIN airline al ON f.airline_id = al.airline_id
JOIN airplane ap ON f.airplane_id = ap.airplane_id
WHERE from_airport.iata = 'BOI'
    AND f.departure >= @last_week_start
    AND f.departure <= @last_week_end
ORDER BY f.departure
LIMIT 8;

-- ============================================================================
-- TIER 5: Local Airport (1-9 routes) - Billings (BIL)
-- Expected: 1-3 flights per week
-- ============================================================================

SELECT 
    'TIER 5 - BIL (Local Airport)' as tier,
    f.flight_id,
    f.flightno,
    from_airport.iata as departure_airport,
    from_airport.name as departure_city,
    to_airport.iata as arrival_airport,
    to_airport.name as arrival_city,
    f.departure,
    f.arrival,
    al.iata as airline_code,
    al.airlinename as airline_name,
    ap.capacity as aircraft_capacity,
    DAYNAME(f.departure) as day_of_week
FROM flight f
JOIN airport from_airport ON f.from = from_airport.airport_id
JOIN airport to_airport ON f.to = to_airport.airport_id
JOIN airline al ON f.airline_id = al.airline_id
JOIN airplane ap ON f.airplane_id = ap.airplane_id
WHERE from_airport.iata = 'BIL'
    AND f.departure >= @last_week_start
    AND f.departure <= @last_week_end
ORDER BY f.departure
LIMIT 5;

-- ============================================================================
-- SUMMARY QUERY: Flight frequency analysis by tier
-- ============================================================================

SELECT 
    'SUMMARY - Flight Frequency by Tier' as analysis,
    tier_info.tier,
    tier_info.airport_code,
    tier_info.expected_frequency,
    COUNT(f.flight_id) as actual_flights_last_week,
    ROUND(COUNT(f.flight_id) / 7, 1) as avg_flights_per_day
FROM (
    SELECT 'Tier 1' as tier, 'ATL' as airport_code, '6-12 daily' as expected_frequency
    UNION ALL
    SELECT 'Tier 2' as tier, 'DEN' as airport_code, '2-6 daily' as expected_frequency
    UNION ALL
    SELECT 'Tier 3' as tier, 'BNA' as airport_code, '1-3 daily' as expected_frequency
    UNION ALL
    SELECT 'Tier 4' as tier, 'BOI' as airport_code, '3-7 weekly' as expected_frequency
    UNION ALL
    SELECT 'Tier 5' as tier, 'BIL' as airport_code, '1-3 weekly' as expected_frequency
) tier_info
LEFT JOIN airport a ON a.iata = tier_info.airport_code
LEFT JOIN flight f ON f.from = a.airport_id 
    AND f.departure >= @last_week_start 
    AND f.departure <= @last_week_end
GROUP BY tier_info.tier, tier_info.airport_code, tier_info.expected_frequency
ORDER BY tier_info.tier;

-- ============================================================================
-- ALTERNATIVE QUERY: If specific IATA codes don't exist, use airport names
-- ============================================================================

-- Find available airports that might match tier criteria
SELECT 
    'Available Airports for Testing' as info,
    a.iata,
    a.name,
    COUNT(f.flight_id) as flights_last_week
FROM airport a
LEFT JOIN flight f ON f.from = a.airport_id 
    AND f.departure >= @last_week_start 
    AND f.departure <= @last_week_end
WHERE a.iata IS NOT NULL 
    AND a.iata != ''
GROUP BY a.airport_id, a.iata, a.name
HAVING flights_last_week > 0
ORDER BY flights_last_week DESC
LIMIT 20;

-- ============================================================================
-- PEAK HOURS ANALYSIS: Check if flights follow expected patterns
-- ============================================================================

SELECT 
    'Peak Hours Analysis' as analysis,
    HOUR(f.departure) as departure_hour,
    COUNT(*) as flight_count,
    CASE 
        WHEN HOUR(f.departure) BETWEEN 6 AND 9 THEN 'Morning Peak'
        WHEN HOUR(f.departure) BETWEEN 12 AND 14 THEN 'Midday Peak'
        WHEN HOUR(f.departure) BETWEEN 18 AND 21 THEN 'Evening Peak'
        ELSE 'Off-Peak'
    END as time_category
FROM flight f
JOIN airport a ON f.from = a.airport_id
WHERE a.iata IN ('ATL', 'DEN', 'BNA', 'BOI', 'BIL')
    AND f.departure >= @last_week_start
    AND f.departure <= @last_week_end
GROUP BY HOUR(f.departure)
ORDER BY departure_hour;