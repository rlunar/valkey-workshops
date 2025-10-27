#!/usr/bin/env python3
"""
Reassign flights to larger aircraft to increase passenger capacity

This script reassigns flights from small aircraft to larger ones to achieve
higher passenger counts per flight.
"""

import random
import argparse
import sys
import os
from sqlmodel import Session, select, func, text

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.flight import Flight
from models.airplane import Airplane


def reassign_to_larger_aircraft(min_capacity: int = 150, verbose: bool = False):
    """Reassign flights to aircraft with at least min_capacity seats"""
    
    print(f"🚀 Reassigning flights to larger aircraft (min {min_capacity} seats)")
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Get current flight statistics
        current_stats = session.exec(
            select(
                func.count(Flight.flight_id).label('total_flights'),
                func.avg(Airplane.capacity).label('avg_capacity'),
                func.min(Airplane.capacity).label('min_capacity'),
                func.max(Airplane.capacity).label('max_capacity')
            )
            .select_from(Flight)
            .join(Airplane, Flight.airplane_id == Airplane.airplane_id)
        ).first()
        
        print(f"   📊 Current stats:")
        print(f"      Total flights: {current_stats.total_flights:,}")
        print(f"      Average capacity: {float(current_stats.avg_capacity):.1f} seats")
        print(f"      Capacity range: {current_stats.min_capacity} - {current_stats.max_capacity} seats")
        
        # Get large aircraft (capacity >= min_capacity)
        large_aircraft = session.exec(
            select(Airplane.airplane_id, Airplane.capacity)
            .where(Airplane.capacity >= min_capacity)
        ).all()
        
        if not large_aircraft:
            print(f"❌ No aircraft found with capacity >= {min_capacity} seats")
            return
        
        print(f"   ✈️  Found {len(large_aircraft)} large aircraft (>= {min_capacity} seats)")
        
        # Get flights using small aircraft
        small_aircraft_flights = session.exec(
            select(Flight.flight_id, Flight.airplane_id, Airplane.capacity)
            .join(Airplane, Flight.airplane_id == Airplane.airplane_id)
            .where(Airplane.capacity < min_capacity)
        ).all()
        
        print(f"   🔄 Found {len(small_aircraft_flights)} flights using small aircraft")
        
        if not small_aircraft_flights:
            print("   ✅ All flights already use large aircraft!")
            return
        
        # Reassign flights to large aircraft
        reassigned_count = 0
        batch_size = 1000
        
        for i, (flight_id, old_airplane_id, old_capacity) in enumerate(small_aircraft_flights):
            # Pick a random large aircraft
            new_airplane_id, new_capacity = random.choice(large_aircraft)
            
            # Update the flight
            update_stmt = text("UPDATE flight SET airplane_id = :new_id WHERE flight_id = :flight_id")
            session.execute(update_stmt, {"new_id": new_airplane_id, "flight_id": flight_id})
            
            reassigned_count += 1
            
            if verbose and reassigned_count % batch_size == 0:
                print(f"   ⚡ Reassigned {reassigned_count:,}/{len(small_aircraft_flights):,} flights")
        
        # Commit all changes
        session.commit()
        
        # Get new statistics
        new_stats = session.exec(
            select(
                func.avg(Airplane.capacity).label('avg_capacity'),
                func.min(Airplane.capacity).label('min_capacity'),
                func.max(Airplane.capacity).label('max_capacity')
            )
            .select_from(Flight)
            .join(Airplane, Flight.airplane_id == Airplane.airplane_id)
        ).first()
        
        print(f"\n🎉 Reassignment completed!")
        print(f"   📈 Reassigned {reassigned_count:,} flights")
        print(f"   📊 New stats:")
        print(f"      Average capacity: {float(new_stats.avg_capacity):.1f} seats")
        print(f"      Capacity range: {new_stats.min_capacity} - {new_stats.max_capacity} seats")
        
        capacity_improvement = float(new_stats.avg_capacity) - float(current_stats.avg_capacity)
        print(f"   📈 Capacity improvement: +{capacity_improvement:.1f} seats per flight")
        
        # Estimate new booking potential
        estimated_bookings = int(current_stats.total_flights * float(new_stats.avg_capacity) * 0.90)
        print(f"   🎯 Estimated bookings at 90% occupancy: {estimated_bookings:,}")
        print(f"   👥 Estimated passengers per flight: {float(new_stats.avg_capacity) * 0.90:.1f}")


def main():
    parser = argparse.ArgumentParser(description='Reassign flights to larger aircraft')
    parser.add_argument('--min-capacity', type=int, default=150,
                       help='Minimum aircraft capacity in seats (default: 150)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.min_capacity <= 0:
        print("❌ Error: min-capacity must be positive")
        return 1
    
    try:
        reassign_to_larger_aircraft(args.min_capacity, args.verbose)
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())