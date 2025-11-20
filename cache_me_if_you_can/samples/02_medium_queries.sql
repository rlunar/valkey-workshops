-- ============================================
-- MEDIUM QUERIES - Joins and Filtering
-- ============================================

-- 1. Get passenger with their details by passenger ID
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

-- 2. Find passengers by country
SELECT 
    p.passenger_id,
    p.passportno,
    p.firstname,
    p.lastname,
    pd.city,
    pd.country
FROM passenger p
INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
WHERE pd.country = 'Germany'
LIMIT 20;

-- 3. Find passenger by passport number
SELECT 
    p.passenger_id,
    p.passportno,
    p.firstname,
    p.lastname,
    pd.country,
    pd.emailaddress
FROM passenger p
LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
WHERE p.passportno = 'P103014';

-- 4. Get passengers from a specific country with passport filter
SELECT 
    p.passenger_id,
    p.passportno,
    p.firstname,
    p.lastname,
    pd.city,
    pd.country,
    pd.emailaddress
FROM passenger p
INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
WHERE pd.country = 'United States'
  AND p.passportno LIKE 'P10%'
LIMIT 10;

-- 5. Get flight with airline information
SELECT 
    f.flight_id,
    f.flightno,
    f.departure,
    f.arrival,
    a.airlinename,
    a.iata as airline_code
FROM flight f
INNER JOIN airline a ON f.airline_id = a.airline_id
WHERE f.flight_id = 115;

-- 6. Get flights between specific airports
SELECT 
    f.flight_id,
    f.flightno,
    f.departure,
    f.arrival,
    a_from.name as departure_airport,
    a_to.name as arrival_airport
FROM flight f
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
WHERE a_from.iata = 'JFK' 
  AND a_to.iata = 'FCM'
LIMIT 10;

-- 6b. Find all distinct flights departing from JFK
SELECT DISTINCT
    a_to.airport_id as destination_airport_id,
    a_to.iata as destination_iata,
    a_to.name as destination_airport,
    a_to_geo.city as destination_city,
    a_to_geo.country as destination_country,
    COUNT(f.flight_id) as number_of_flights
FROM flight f
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
LEFT JOIN airport_geo a_to_geo ON a_to.airport_id = a_to_geo.airport_id
WHERE a_from.iata = 'JFK'
GROUP BY a_to.airport_id, a_to.iata, a_to.name, a_to_geo.city, a_to_geo.country
ORDER BY number_of_flights DESC;

-- 7. Get airline with its base airport details
SELECT 
    al.airline_id,
    al.iata,
    al.airlinename,
    ap.name as base_airport_name,
    ap.iata as base_airport_code
FROM airline al
INNER JOIN airport ap ON al.base_airport = ap.airport_id
WHERE al.airline_id = 1;

-- 8. Count bookings per passenger
SELECT 
    p.passenger_id,
    p.firstname,
    p.lastname,
    COUNT(b.booking_id) as total_bookings
FROM passenger p
INNER JOIN booking b ON p.passenger_id = b.passenger_id
GROUP BY p.passenger_id, p.firstname, p.lastname
ORDER BY total_bookings DESC
LIMIT 10;

-- 9. Get airplane with type information
SELECT 
    ap.airplane_id,
    ap.capacity,
    apt.identifier as airplane_type,
    apt.description,
    al.airlinename
FROM airplane ap
INNER JOIN airplane_type apt ON ap.type_id = apt.type_id
INNER JOIN airline al ON ap.airline_id = al.airline_id
WHERE ap.airplane_id = 100;

-- 10. Find passengers by city and country
SELECT 
    p.passenger_id,
    p.firstname,
    p.lastname,
    p.passportno,
    pd.city,
    pd.country
FROM passenger p
INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
WHERE pd.city = 'New York'
  AND pd.country = 'United States'
LIMIT 15;
