-- ============================================
-- SIMPLE QUERIES - Single Table Operations
-- ============================================

-- 1. Fetch a single airline by ID
SELECT 
    airline_id,
    iata,
    airlinename,
    base_airport
FROM airline
WHERE airline_id = 1;

-- 2. Fetch airline by IATA code
SELECT 
    airline_id,
    iata,
    airlinename,
    base_airport
FROM airline
WHERE iata = 'LH';

-- 3. Get all airlines (limit 10)
SELECT 
    airline_id,
    iata,
    airlinename,
    base_airport
FROM airline
LIMIT 10;

-- 4. Fetch a single airport by ICAO code
SELECT 
    airport_id,
    iata,
    icao,
    name
FROM airport
WHERE icao = 'KJFK';

-- 5. Get airport by IATA code
SELECT 
    airport_id,
    iata,
    icao,
    name
FROM airport
WHERE iata = 'JFK';

-- 6. Find airports by name pattern
SELECT 
    airport_id,
    iata,
    icao,
    name
FROM airport
WHERE name LIKE '%International%'
LIMIT 10;

-- 7. Get a specific flight by ID
SELECT 
    flight_id,
    flightno,
    `from`,
    `to`,
    departure,
    arrival,
    airline_id
FROM flight
WHERE flight_id = 115;

-- 8. Count total passengers
SELECT COUNT(*) as total_passengers
FROM passenger;

-- 9. Count total bookings
SELECT COUNT(*) as total_bookings
FROM booking;

-- 10. Get employee by username
SELECT 
    employee_id,
    firstname,
    lastname,
    department,
    emailaddress
FROM employee
WHERE username = 'admin';
