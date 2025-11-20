-- ============================================
-- SIMPLE QUERIES - Single Table Operations
-- ============================================

USE flughafendb_large;

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
FROM
	airline
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

-- 10. Count distict passports
SELECT COUNT(DISTINCT(passportno)) as different_passports
FROM passenger;

-- 11. Get employee by username
SELECT 
    employee_id,
    firstname,
    lastname,
    department,
    emailaddress
FROM employee
WHERE username = 'admin';


-- 12. Get passenger with details by passenger ID
SELECT 
    p.passenger_id,
    p.passportno,
    p.firstname,
    p.lastname,
    pd.birthdate,
    pd.sex,
    pd.street,
    pd.city,
    pd.zip,
    pd.country,
    pd.emailaddress,
    pd.telephoneno
FROM passenger p
LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
WHERE p.passenger_id = 1000;

-- 13. Get airport with geographic details by airport ID
SELECT 
    a.airport_id,
    a.iata,
    a.icao,
    a.name,
    ag.city,
    ag.country,
    ag.latitude,
    ag.longitude
FROM airport a
LEFT JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE a.airport_id = 3797;

-- 14. Get airport with geographic details by IATA code
SELECT 
    a.airport_id,
    a.iata,
    a.icao,
    a.name,
    ag.city,
    ag.country,
    ag.latitude,
    ag.longitude
FROM airport a
LEFT JOIN airport_geo ag ON a.airport_id = ag.airport_id
WHERE a.iata = 'JFK';

