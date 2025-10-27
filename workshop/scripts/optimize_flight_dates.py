#!/usr/bin/env python3
"""
Optimize Flight Dates Script

This script clears existing flights and regenerates only flights for 2025 and first half of 2026
to speed up booking population.
"""

import os
import sys
from datetime import datetime
from sqlmodel import Session, select, func, text

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.flight import Flight
from models.booking import Booking


def clear_old_flights_and_bookings():
    """Clear all existing flights and bookings"""
    print("🗑️  Clearing existing flights and bookings...")
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Count existing data
        flight_count = session.exec(select(func.count(Flight.flight_id))).first()
        booking_count = session.exec(select(func.count(Booking.booking_id))).first()
        
        print(f"   Found {flight_count:,} flights and {booking_count:,} bookings")
        
        if flight_count == 0 and booking_count == 0:
            print("   No data to clear")
            return
        
        # Clear bookings first (due to foreign key constraints)
        if booking_count > 0:
            print("   Clearing bookings...")
            session.execute(text('DELETE FROM booking'))
            session.commit()
            print(f"   ✅ Cleared {booking_count:,} bookings")
        
        # Clear flights
        if flight_count > 0:
            print("   Clearing flights...")
            session.execute(text('DELETE FROM flight'))
            session.commit()
            print(f"   ✅ Cleared {flight_count:,} flights")
        
        print("✅ Database cleared successfully")


def regenerate_optimized_flights():
    """Regenerate flights for 2025 and first half of 2026"""
    print("\n🛫 Regenerating flights for optimized date range...")
    print("   Date range: 2025-01-01 to 2026-06-30")
    print("   This will significantly reduce the number of flights and speed up booking population")
    
    # Import and run the comprehensive flight population
    try:
        from scripts.populate_flights_comprehensive import ComprehensiveFlightPopulator, DatabaseManager
        
        db_manager = DatabaseManager()
        populator = ComprehensiveFlightPopulator(db_manager, verbose=False, flight_reduction_factor=0.2)
        
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2026, 6, 30)
        
        flights_created = populator.populate_flights(start_date, end_date, max_routes=1000)
        
        print(f"✅ Created {flights_created:,} flights for optimized date range")
        return flights_created
        
    except Exception as e:
        print(f"❌ Error during flight generation: {e}")
        print("\nYou can manually run flight population with:")
        print("   uv run python scripts/populate_flights_comprehensive.py --no-reset")
        return 0


def main():
    print("🚀 Flight Date Optimization Script")
    print("=" * 50)
    print("This script will:")
    print("  1. Clear all existing flights and bookings")
    print("  2. Regenerate flights only for 2025 and first half of 2026")
    print("  3. Significantly reduce booking population time")
    print()
    
    response = input("Continue with optimization? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled")
        return 0
    
    try:
        # Step 1: Clear existing data
        clear_old_flights_and_bookings()
        
        # Step 2: Regenerate optimized flights
        flights_created = regenerate_optimized_flights()
        
        if flights_created > 0:
            print(f"\n🎉 Optimization completed successfully!")
            print(f"   New flight count: {flights_created:,}")
            print(f"   Date range: 2025-01-01 to 2026-06-30")
            print("\nNext steps:")
            print("   • Run booking population: uv run python scripts/populate_bookings_optimized.py --clear")
            print("   • This should now complete much faster!")
        else:
            print("\n⚠️  Flight generation failed. Please check the error messages above.")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())