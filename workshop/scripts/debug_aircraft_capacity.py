#!/usr/bin/env python3
"""
Debug script to check aircraft capacities and booking logic
"""

import sys
import os
from sqlmodel import Session, select, text

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.flight import Flight
from models.airplane import Airplane
from models.booking import Booking


def debug_aircraft_capacity():
    """Check aircraft capacities and current booking patterns"""
    
    print("🔍 Debugging aircraft capacity and booking patterns...")
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Check aircraft capacity distribution
        capacity_stats = session.exec(text("""
            SELECT 
                a.capacity,
                COUNT(*) as aircraft_count,
                COUNT(DISTINCT f.flight_id) as flight_count
            FROM airplane a
            LEFT JOIN flight f ON a.airplane_id = f.airplane_id
            GROUP BY a.capacity
            ORDER BY a.capacity DESC
            LIMIT 20
        """)).all()
        
        print("✈️  Aircraft capacity distribution:")
        total_capacity = 0
        total_aircraft = 0
        
        for capacity, aircraft_count, flight_count in capacity_stats:
            print(f"   Capacity {capacity}: {aircraft_count} aircraft, {flight_count} flights")
            total_capacity += capacity * aircraft_count
            total_aircraft += aircraft_count
        
        if total_aircraft > 0:
            avg_capacity = total_capacity / total_aircraft
            print(f"   Average aircraft capacity: {avg_capacity:.1f}")
        
        # Check current booking patterns
        booking_stats = session.exec(text("""
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
            ORDER BY a.capacity DESC, occupancy_pct DESC
            LIMIT 15
        """)).all()
        
        print(f"\n📊 Current booking patterns (largest aircraft first):")
        for flightno, capacity, booked, occupancy in booking_stats:
            print(f"   {flightno}: {booked}/{capacity} ({occupancy}%) - Capacity: {capacity}")
        
        # Test occupancy calculation logic
        print(f"\n🧪 Testing occupancy calculation logic:")
        from scripts.populate_bookings_optimized import OptimizedBookingPopulator
        from datetime import datetime
        
        populator = OptimizedBookingPopulator(verbose=True)
        
        # Test with different times and capacities
        test_times = [
            datetime(2024, 6, 10, 8, 0),   # Monday 8 AM (peak)
            datetime(2024, 6, 10, 14, 0),  # Monday 2 PM (peak)
            datetime(2024, 6, 15, 22, 0),  # Saturday 10 PM (off-peak)
        ]
        
        test_capacities = [150, 250, 350]
        
        for test_time in test_times:
            is_peak = populator.is_peak_time(test_time)
            occupancy_rate = populator.calculate_occupancy_rate(test_time)
            
            print(f"   {test_time.strftime('%A %I %p')}: Peak={is_peak}, Rate={occupancy_rate:.1%}")
            
            for capacity in test_capacities:
                target_passengers = int(capacity * occupancy_rate)
                min_passengers = max(1, int(capacity * 0.70))
                final_target = max(target_passengers, min_passengers)
                final_target = min(final_target, capacity)
                
                print(f"     Capacity {capacity}: Target={target_passengers}, Min={min_passengers}, Final={final_target}")


if __name__ == "__main__":
    debug_aircraft_capacity()