#!/usr/bin/env python3
"""
Test script to validate high occupancy and frequent flyer improvements
"""

import sys
import os
from sqlmodel import Session, select, func, text

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.booking import Booking
from models.flight import Flight
from models.airplane import Airplane
from scripts.populate_bookings_optimized import populate_bookings_optimized


def test_high_occupancy():
    """Test the improved booking system"""
    
    print("🧪 Testing high occupancy booking system...")
    
    # Test with 50 flights
    populate_bookings_optimized(
        clear_existing=True,
        max_flights=50,
        batch_size=1000,
        verbose=True
    )
    
    # Analyze results
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Check occupancy rates
        occupancy_stats = session.exec(text("""
            SELECT 
                f.flightno,
                a.capacity,
                COUNT(b.booking_id) as booked,
                ROUND(COUNT(b.booking_id) * 100.0 / a.capacity, 1) as occupancy_pct
            FROM flight f
            JOIN airplane a ON f.airplane_id = a.airplane_id
            LEFT JOIN booking b ON f.flight_id = b.flight_id
            GROUP BY f.flight_id, f.flightno, a.capacity
            HAVING COUNT(b.booking_id) > 0
            ORDER BY occupancy_pct DESC
            LIMIT 10
        """)).all()
        
        print(f"\n📊 Top 10 flights by occupancy:")
        total_occupancy = 0
        flight_count = 0
        
        for flightno, capacity, booked, occupancy in occupancy_stats:
            print(f"   {flightno}: {booked}/{capacity} ({occupancy}%)")
            total_occupancy += occupancy
            flight_count += 1
        
        if flight_count > 0:
            avg_occupancy = total_occupancy / flight_count
            print(f"\n   Average occupancy: {avg_occupancy:.1f}%")
            
            if avg_occupancy < 80:
                print("   ⚠️  Occupancy still seems low")
            else:
                print("   ✅ Good occupancy rates!")
        
        # Check for frequent flyers
        frequent_flyer_stats = session.exec(text("""
            SELECT 
                passenger_id,
                COUNT(*) as flight_count
            FROM booking
            GROUP BY passenger_id
            HAVING COUNT(*) > 1
            ORDER BY flight_count DESC
            LIMIT 10
        """)).all()
        
        print(f"\n👥 Top frequent flyers:")
        if frequent_flyer_stats:
            for passenger_id, flight_count in frequent_flyer_stats:
                print(f"   Passenger {passenger_id}: {flight_count} flights")
            print("   ✅ Frequent flyers detected!")
        else:
            print("   ⚠️  No frequent flyers found")
        
        # Overall stats
        total_bookings = session.exec(select(func.count(Booking.booking_id))).first()
        total_flights_with_bookings = session.exec(text("""
            SELECT COUNT(DISTINCT flight_id) FROM booking
        """)).first()
        
        print(f"\n📈 Overall stats:")
        print(f"   Total bookings: {total_bookings:,}")
        print(f"   Flights with bookings: {total_flights_with_bookings}")
        
        if total_flights_with_bookings > 0:
            avg_bookings_per_flight = total_bookings / total_flights_with_bookings
            print(f"   Average bookings per flight: {avg_bookings_per_flight:.1f}")


if __name__ == "__main__":
    test_high_occupancy()