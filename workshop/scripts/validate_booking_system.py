#!/usr/bin/env python3
"""
Validation script for the booking population system
Checks data integrity and business rule compliance
"""

import sys
import os
from datetime import datetime, timedelta
from sqlmodel import Session, select, func, and_, text

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.booking import Booking
from models.flight import Flight
from models.passenger import Passenger
from models.airplane import Airplane


def validate_booking_system():
    """Validate the booking system data integrity"""
    
    print("🔍 Validating booking system...")
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Basic counts
        booking_count = session.exec(select(func.count(Booking.booking_id))).first()
        flight_count = session.exec(select(func.count(Flight.flight_id))).first()
        passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
        
        print(f"📊 Database Overview:")
        print(f"   Bookings: {booking_count:,}")
        print(f"   Flights: {flight_count:,}")
        print(f"   Passengers: {passenger_count:,}")
        
        if booking_count == 0:
            print("⚠️  No bookings found. Run populate_bookings.py first.")
            return
        
        # Check 1: No duplicate seats per flight
        print("\n🔍 Checking for duplicate seats per flight...")
        duplicate_seats = session.exec(text("""
            SELECT flight_id, seat, COUNT(*) as count
            FROM booking 
            GROUP BY flight_id, seat 
            HAVING COUNT(*) > 1
            LIMIT 10
        """)).all()
        
        if duplicate_seats:
            print(f"❌ Found {len(duplicate_seats)} duplicate seat assignments!")
            for flight_id, seat, count in duplicate_seats:
                print(f"   Flight {flight_id}, Seat {seat}: {count} bookings")
        else:
            print("✅ No duplicate seats found")
        
        # Check 2: Occupancy rates
        print("\n📈 Analyzing occupancy rates...")
        occupancy_stats = session.exec(text("""
            SELECT 
                f.flight_id,
                f.flightno,
                f.departure,
                a.capacity,
                COUNT(b.booking_id) as booked,
                ROUND(COUNT(b.booking_id) * 100.0 / a.capacity, 1) as occupancy_pct
            FROM flight f
            JOIN airplane a ON f.airplane_id = a.airplane_id
            LEFT JOIN booking b ON f.flight_id = b.flight_id
            GROUP BY f.flight_id, f.flightno, f.departure, a.capacity
            ORDER BY occupancy_pct DESC
            LIMIT 10
        """)).all()
        
        if occupancy_stats:
            print("   Top 10 flights by occupancy:")
            for flight_id, flightno, departure, capacity, booked, occupancy in occupancy_stats:
                print(f"   {flightno}: {booked}/{capacity} ({occupancy}%) - {departure}")
        
        # Check 3: Price distribution
        print("\n💰 Analyzing price distribution...")
        price_stats = session.exec(text("""
            SELECT 
                MIN(price) as min_price,
                AVG(price) as avg_price,
                MAX(price) as max_price,
                COUNT(*) as total_bookings
            FROM booking
        """)).first()
        
        if price_stats:
            min_price, avg_price, max_price, total = price_stats
            print(f"   Price range: ${min_price:.2f} - ${max_price:.2f}")
            print(f"   Average price: ${avg_price:.2f}")
            print(f"   Total bookings: {total:,}")
        
        # Check 4: Seat class distribution
        print("\n💺 Analyzing seat assignments...")
        seat_patterns = session.exec(text("""
            SELECT 
                CASE 
                    WHEN seat LIKE 'F%' THEN 'First Class'
                    WHEN seat LIKE 'B%' THEN 'Business Class'
                    ELSE 'Economy Class'
                END as seat_class,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM booking), 1) as percentage
            FROM booking
            GROUP BY seat_class
            ORDER BY count DESC
        """)).all()
        
        for seat_class, count, percentage in seat_patterns:
            print(f"   {seat_class}: {count:,} ({percentage}%)")
        
        # Check 5: Peak vs off-peak distribution
        print("\n⏰ Analyzing peak time distribution...")
        peak_analysis = session.exec(text("""
            SELECT 
                CASE 
                    WHEN HOUR(f.departure) BETWEEN 6 AND 22 
                         AND WEEKDAY(f.departure) BETWEEN 0 AND 3 THEN 'Peak Time'
                    ELSE 'Off-Peak Time'
                END as time_category,
                COUNT(DISTINCT f.flight_id) as flights,
                COUNT(b.booking_id) as bookings,
                ROUND(AVG(occupancy.occupancy_pct), 1) as avg_occupancy
            FROM flight f
            LEFT JOIN booking b ON f.flight_id = b.flight_id
            JOIN (
                SELECT 
                    f2.flight_id,
                    COUNT(b2.booking_id) * 100.0 / a2.capacity as occupancy_pct
                FROM flight f2
                JOIN airplane a2 ON f2.airplane_id = a2.airplane_id
                LEFT JOIN booking b2 ON f2.flight_id = b2.flight_id
                GROUP BY f2.flight_id, a2.capacity
            ) occupancy ON f.flight_id = occupancy.flight_id
            GROUP BY time_category
        """)).all()
        
        for category, flights, bookings, avg_occupancy in peak_analysis:
            print(f"   {category}: {flights:,} flights, {bookings:,} bookings, {avg_occupancy}% avg occupancy")
        
        # Check 6: Passenger booking frequency
        print("\n👥 Analyzing passenger booking patterns...")
        passenger_stats = session.exec(text("""
            SELECT 
                bookings_per_passenger,
                COUNT(*) as passenger_count
            FROM (
                SELECT passenger_id, COUNT(*) as bookings_per_passenger
                FROM booking
                GROUP BY passenger_id
            ) passenger_bookings
            GROUP BY bookings_per_passenger
            ORDER BY bookings_per_passenger
            LIMIT 10
        """)).all()
        
        print("   Bookings per passenger distribution:")
        for bookings_per_passenger, passenger_count in passenger_stats:
            print(f"   {bookings_per_passenger} booking(s): {passenger_count:,} passengers")
        
        print("\n✅ Booking system validation completed!")


if __name__ == "__main__":
    validate_booking_system()