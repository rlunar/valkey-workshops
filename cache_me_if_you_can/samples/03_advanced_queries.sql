-- ============================================
-- ADVANCED QUERIES - Complex Joins & Aggregations
-- ============================================

USE flughafendb_large;

-- 1. Last 10 passenger bookings with full flight and airport details
SELECT 
    b.booking_id,
    b.seat,
    b.price,
    p.firstname,
    p.lastname,
    p.passportno,
    f.flightno,
    f.departure,
    f.arrival,
    a_from.name as departure_airport,
    a_from.iata as departure_iata,
    a_to.name as arrival_airport,
    a_to.iata as arrival_iata,
    al.airlinename,
    al.iata as airline_code
FROM booking b
INNER JOIN passenger p ON b.passenger_id = p.passenger_id
INNER JOIN flight f ON b.flight_id = f.flight_id
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
INNER JOIN airline al ON f.airline_id = al.airline_id
ORDER BY b.booking_id DESC
LIMIT 10;

-- 2. Passenger's complete booking history with airport details
SELECT 
    p.passenger_id,
    p.firstname,
    p.lastname,
    b.booking_id,
    b.seat,
    b.price,
    f.flightno,
    f.departure,
    f.arrival,
    a_from.name as departure_airport,
    a_from.iata as departure_iata,
    a_to.name as arrival_airport,
    a_to.iata as arrival_iata,
    al.airlinename
FROM passenger p
INNER JOIN booking b ON p.passenger_id = b.passenger_id
INNER JOIN flight f ON b.flight_id = f.flight_id
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
INNER JOIN airline al ON f.airline_id = al.airline_id
WHERE p.passenger_id = 1000
ORDER BY f.departure DESC;


-- 3. Upcoming flights for a passenger with full details
SELECT 
    p.firstname,
    p.lastname,
    pd.emailaddress,
    b.seat,
    b.price,
    f.flightno,
    f.departure,
    f.arrival,
    a_from.name as departure_airport,
#    a_from.city as departure_city,
    a_to.name as arrival_airport,
#    a_to.city as arrival_city,
    al.airlinename,
    apt.identifier as airplane_type,
    ap.capacity as airplane_capacity
FROM passenger p
INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
INNER JOIN booking b ON p.passenger_id = b.passenger_id
INNER JOIN flight f ON b.flight_id = f.flight_id
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
LEFT JOIN airport_geo ag_from ON a_from.airport_id = ag_from.airport_id
LEFT JOIN airport_geo ag_to ON a_to.airport_id = ag_to.airport_id
INNER JOIN airline al ON f.airline_id = al.airline_id
INNER JOIN airplane ap ON f.airplane_id = ap.airplane_id
INNER JOIN airplane_type apt ON ap.type_id = apt.type_id
WHERE p.passenger_id = 1000
  AND f.departure > NOW()
ORDER BY f.departure ASC;

-- 4. Flight manifest - all passengers on a specific flight
SELECT 
    b.seat,
    p.firstname,
    p.lastname,
    p.passportno,
    pd.country,
    b.price
FROM booking b
INNER JOIN passenger p ON b.passenger_id = p.passenger_id
LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
WHERE b.flight_id = 115
ORDER BY b.seat ASC;

-- 5. Revenue analysis by route (top 10 routes)
SELECT 
    a_from.name as departure_airport,
    a_from.iata as from_iata,
    a_to.name as arrival_airport,
    a_to.iata as to_iata,
    COUNT(DISTINCT f.flight_id) as total_flights,
    COUNT(b.booking_id) as total_bookings,
    SUM(b.price) as total_revenue,
    AVG(b.price) as avg_ticket_price
FROM flight f
INNER JOIN booking b ON f.flight_id = b.flight_id
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
GROUP BY a_from.airport_id, a_from.name, a_from.iata, 
         a_to.airport_id, a_to.name, a_to.iata
ORDER BY total_revenue DESC
LIMIT 10;

-- 6. Passenger travel statistics with country information
SELECT 
    p.passenger_id,
    p.firstname,
    p.lastname,
    pd.country,
    pd.city,
    COUNT(b.booking_id) as total_flights,
    SUM(b.price) as total_spent,
    AVG(b.price) as avg_ticket_price,
    MIN(f.departure) as first_flight_date,
    MAX(f.departure) as last_flight_date
FROM passenger p
INNER JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
INNER JOIN booking b ON p.passenger_id = b.passenger_id
INNER JOIN flight f ON b.flight_id = f.flight_id
GROUP BY p.passenger_id, p.firstname, p.lastname, pd.country, pd.city
HAVING total_flights >= 5
ORDER BY total_flights DESC
LIMIT 20;

-- 7. Detailed flight information with all related entities
SELECT 
    f.flight_id,
    f.flightno,
    f.departure,
    f.arrival,
    TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) as duration_minutes,
    a_from.name as departure_airport,
    a_from.iata as from_iata,
    ag_from.city as from_city,
    ag_from.country as from_country,
    a_to.name as arrival_airport,
    a_to.iata as to_iata,
    ag_to.city as to_city,
    ag_to.country as to_country,
    al.airlinename,
    al.iata as airline_code,
    apt.identifier as airplane_type,
    ap.capacity,
    COUNT(b.booking_id) as seats_booked,
    (ap.capacity - COUNT(b.booking_id)) as seats_available
FROM flight f
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
LEFT JOIN airport_geo ag_from ON a_from.airport_id = ag_from.airport_id
LEFT JOIN airport_geo ag_to ON a_to.airport_id = ag_to.airport_id
INNER JOIN airline al ON f.airline_id = al.airline_id
INNER JOIN airplane ap ON f.airplane_id = ap.airplane_id
INNER JOIN airplane_type apt ON ap.type_id = apt.type_id
LEFT JOIN booking b ON f.flight_id = b.flight_id
WHERE f.flight_id = 115
GROUP BY f.flight_id, f.flightno, f.departure, f.arrival,
         a_from.name, a_from.iata, ag_from.city, ag_from.country,
         a_to.name, a_to.iata, ag_to.city, ag_to.country,
         al.airlinename, al.iata, apt.identifier, ap.capacity;

-- 8. Busiest routes by passenger count
SELECT 
    a_from.name as departure_airport,
    a_from.iata as from_iata,
    a_to.name as arrival_airport,
    a_to.iata as to_iata,
    COUNT(DISTINCT f.flight_id) as number_of_flights,
    COUNT(b.booking_id) as total_passengers,
    ROUND(COUNT(b.booking_id) / COUNT(DISTINCT f.flight_id), 2) as avg_passengers_per_flight
FROM flight f
INNER JOIN booking b ON f.flight_id = b.flight_id
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
GROUP BY a_from.airport_id, a_from.name, a_from.iata,
         a_to.airport_id, a_to.name, a_to.iata
ORDER BY total_passengers DESC
LIMIT 15;

-- 9. Airline performance summary
SELECT 
    al.airline_id,
    al.airlinename,
    al.iata,
    COUNT(DISTINCT f.flight_id) as total_flights,
    COUNT(DISTINCT ap.airplane_id) as fleet_size,
    COUNT(b.booking_id) as total_bookings,
    SUM(b.price) as total_revenue,
    AVG(b.price) as avg_ticket_price,
    ROUND(COUNT(b.booking_id) / COUNT(DISTINCT f.flight_id), 2) as avg_passengers_per_flight
FROM airline al
INNER JOIN flight f ON al.airline_id = f.airline_id
INNER JOIN airplane ap ON al.airline_id = ap.airline_id
LEFT JOIN booking b ON f.flight_id = b.flight_id
GROUP BY al.airline_id, al.airlinename, al.iata
ORDER BY total_revenue DESC
LIMIT 10;

-- 10. Recent bookings with passenger details and geographic information
SELECT 
    b.booking_id,
    b.seat,
    b.price,
    p.firstname,
    p.lastname,
    pd.country as passenger_country,
    pd.city as passenger_city,
    f.flightno,
    f.departure,
    f.arrival,
    a_from.name as departure_airport,
    ag_from.city as departure_city,
    ag_from.country as departure_country,
    a_to.name as arrival_airport,
    ag_to.city as arrival_city,
    ag_to.country as arrival_country,
    al.airlinename
FROM booking b
INNER JOIN passenger p ON b.passenger_id = p.passenger_id
LEFT JOIN passengerdetails pd ON p.passenger_id = pd.passenger_id
INNER JOIN flight f ON b.flight_id = f.flight_id
INNER JOIN airport a_from ON f.`from` = a_from.airport_id
INNER JOIN airport a_to ON f.`to` = a_to.airport_id
LEFT JOIN airport_geo ag_from ON a_from.airport_id = ag_from.airport_id
LEFT JOIN airport_geo ag_to ON a_to.airport_id = ag_to.airport_id
INNER JOIN airline al ON f.airline_id = al.airline_id
ORDER BY b.booking_id DESC
LIMIT 10;

