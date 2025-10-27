#!/usr/bin/env python3
"""
Check flight and aircraft capacity statistics to understand booking issues
"""

import sys
import os
from sqlmodel import Session, select, func

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.flight import Flight
from models.airplane import Airplane
from models.booking import Booking

def check_capacity_stats():
    """Check aircraft capacity and flight statistics"""
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Get aircraft capacity statistics
        capacity_stats = session.exec(
            select(
                func.count(Airplane.airplane_id).label('aircraft_count'),
                func.min(Airplane.capacity).label('min_capacity'),
                func.max(Airplane.capacity).label('max_capacity'),
                func.avg(Airplane.capacity).label('avg_capacity')
            )
        ).first()
        
        print("🛩️  Aircraft Capacity Statistics:")
        print(f"   Total aircraft: {capacity_stats.aircraft_count:,}")
        print(f"   Capacity range: {capacity_stats.min_capacity} - {capacity_stats.max_capacity}")
        print(f"   Average capacity: {capacity_stats.avg_capacity:.1f}")
        
        # Get flight statistics
        flight_stats = session.exec(
            select(func.count(Flight.flight_id))
        ).first()
        
        print(f"\n✈️  Flight Statistics:")
        print(f"   Total flights: {flight_stats:,}")
        
        # Get booking statistics
        booking_stats = session.exec(
            select(
                func.count(Booking.booking_id).label('total_bookings'),
                func.count(func.distinct(Booking.passenger_id)).label('unique_passengers')
            )
        ).first()
        
        print(f"\n🎫 Booking Statistics:")
        print(f"   Total bookings: {booking_stats.total_bookings:,}")
        print(f"   Unique passengers: {booking_stats.unique_passengers:,}")
        
        if flight_stats > 0:
            avg_bookings_per_flight = booking_stats.total_bookings / flight_stats
            print(f"   Average bookings per flight: {avg_bookings_per_flight:.1f}")
        
        # Get capacity distribution
        print(f"\n📊 Aircraft Capacity Distribution:")
        capacity_ranges = [
            (0, 50, "Small aircraft (≤50 seats)"),
            (51, 100, "Regional aircraft (51-100 seats)"),
            (101, 200, "Narrow-body (101-200 seats)"),
            (201, 400, "Wide-body (201-400 seats)"),
            (401, 1000, "Large aircraft (400+ seats)")
        ]
        
        for min_cap, max_cap, description in capacity_ranges:
            count = session.exec(
                select(func.count(Airplane.airplane_id))
                .where(Airplane.capacity >= min_cap)
                .where(Airplane.capacity <= max_cap)
            ).first()
            
            if count > 0:
                percentage = (count / capacity_stats.aircraft_count) * 100
                print(f"   {description}: {count:,} aircraft ({percentage:.1f}%)")
        
        # Check flights with their capacities
        print(f"\n🔍 Sample Flight Capacities:")
        sample_flights = session.exec(
            select(Flight.flight_id, Airplane.capacity)
            .join(Airplane, Flight.airplane_id == Airplane.airplane_id)
            .limit(10)
        ).all()
        
        for flight_id, capacity in sample_flights:
            bookings_count = session.exec(
                select(func.count(Booking.booking_id))
                .where(Booking.flight_id == flight_id)
            ).first()
            
            occupancy = (bookings_count / capacity * 100) if capacity > 0 else 0
            print(f"   Flight {flight_id}: {bookings_count}/{capacity} seats ({occupancy:.1f}% full)")
        
        # Recommendations
        print(f"\n💡 Analysis:")
        if capacity_stats.avg_capacity < 100:
            print(f"   ⚠️  Average aircraft capacity is only {capacity_stats.avg_capacity:.1f} seats")
            print(f"   💡 For 100+ passengers per flight, you need larger aircraft")
            print(f"   💡 Consider updating aircraft data with realistic commercial aircraft (150-300 seats)")
        
        if booking_stats.total_bookings / flight_stats < 50:
            print(f"   ⚠️  Current booking rate is very low")
            print(f"   💡 Even with 100% occupancy, you'd only get {capacity_stats.avg_capacity:.1f} passengers per flight")
        
        target_bookings = flight_stats * 100  # 100 passengers per flight target
        print(f"\n🎯 To achieve 100 passengers per flight:")
        print(f"   Need: {target_bookings:,} total bookings")
        print(f"   Current: {booking_stats.total_bookings:,} bookings")
        print(f"   Gap: {target_bookings - booking_stats.total_bookings:,} additional bookings needed")

if __name__ == "__main__":
    check_capacity_stats()