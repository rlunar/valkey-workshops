#!/usr/bin/env python3
"""
Workshop Constraints Validation Script

Validates that the workshop database meets the specified constraints:
- Flights only for 2025 and first half of 2026
- At most 1000 flights per day
- Up to 1 million passengers
- Up to 100 bookings per passenger

Usage:
    python scripts/validate_workshop_constraints.py [--verbose]
"""

import argparse
import sys
import os
from datetime import datetime, date
from sqlmodel import Session, select, text, func

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.flight import Flight
from models.passenger import Passenger
from models.booking import Booking


def validate_flight_date_range(session: Session, verbose: bool = False) -> bool:
    """Validate that flights are only in 2025 and first half of 2026"""
    print("🗓️  Validating flight date range...")
    
    # Check earliest and latest flight dates
    earliest_query = select(func.min(Flight.departure)).where(Flight.departure.is_not(None))
    latest_query = select(func.max(Flight.departure)).where(Flight.departure.is_not(None))
    
    earliest_flight = session.exec(earliest_query).first()
    latest_flight = session.exec(latest_query).first()
    
    if not earliest_flight or not latest_flight:
        print("   ❌ No flights found in database")
        return False
    
    # Convert to dates for comparison
    earliest_date = earliest_flight.date()
    latest_date = latest_flight.date()
    
    # Expected range
    expected_start = date(2025, 1, 1)
    expected_end = date(2026, 6, 30)
    
    if verbose:
        print(f"   Earliest flight: {earliest_date}")
        print(f"   Latest flight: {latest_date}")
        print(f"   Expected range: {expected_start} to {expected_end}")
    
    # Validate range
    date_range_valid = earliest_date >= expected_start and latest_date <= expected_end
    
    if date_range_valid:
        print(f"   ✅ Flight date range is valid: {earliest_date} to {latest_date}")
    else:
        print(f"   ❌ Flight date range is invalid:")
        if earliest_date < expected_start:
            print(f"      Flights start too early: {earliest_date} < {expected_start}")
        if latest_date > expected_end:
            print(f"      Flights end too late: {latest_date} > {expected_end}")
    
    return date_range_valid


def validate_daily_flight_limits(session: Session, verbose: bool = False) -> bool:
    """Validate that there are at most 1000 flights per day"""
    print("✈️  Validating daily flight limits...")
    
    # Get daily flight counts
    daily_counts_query = text("""
        SELECT 
            DATE(departure) as flight_date,
            COUNT(*) as flight_count
        FROM flight
        WHERE departure IS NOT NULL
        GROUP BY DATE(departure)
        ORDER BY flight_count DESC
        LIMIT 10
    """)
    
    daily_counts = session.exec(daily_counts_query).all()
    
    if not daily_counts:
        print("   ❌ No flights found in database")
        return False
    
    max_daily_flights = daily_counts[0].flight_count
    max_date = daily_counts[0].flight_date
    
    if verbose:
        print(f"   Top 10 days by flight count:")
        for flight_date, flight_count in daily_counts:
            status = "✅" if flight_count <= 1000 else "❌"
            print(f"   {status} {flight_date}: {flight_count:,} flights")
    
    # Check if any day exceeds 1000 flights
    over_limit_query = text("""
        SELECT COUNT(*) as days_over_limit
        FROM (
            SELECT DATE(departure) as flight_date, COUNT(*) as flight_count
            FROM flight
            WHERE departure IS NOT NULL
            GROUP BY DATE(departure)
            HAVING COUNT(*) > 1000
        ) over_limit_days
    """)
    
    days_over_limit = session.exec(over_limit_query).first()
    
    if days_over_limit == 0:
        print(f"   ✅ Daily flight limit respected: max {max_daily_flights:,} flights on {max_date}")
        return True
    else:
        print(f"   ❌ Daily flight limit exceeded on {days_over_limit} day(s)")
        print(f"      Highest: {max_daily_flights:,} flights on {max_date}")
        return False


def validate_passenger_count(session: Session, verbose: bool = False) -> bool:
    """Validate that there are up to 1 million passengers"""
    print("👥 Validating passenger count...")
    
    passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
    
    if verbose:
        print(f"   Total passengers: {passenger_count:,}")
    
    if passenger_count <= 1_000_000:
        print(f"   ✅ Passenger count within limit: {passenger_count:,} ≤ 1,000,000")
        return True
    else:
        print(f"   ❌ Passenger count exceeds limit: {passenger_count:,} > 1,000,000")
        return False


def validate_bookings_per_passenger(session: Session, verbose: bool = False) -> bool:
    """Validate that passengers have at most 100 bookings each"""
    print("🎫 Validating bookings per passenger...")
    
    # Get passenger booking distribution
    booking_distribution_query = text("""
        SELECT 
            bookings_per_passenger,
            COUNT(*) as passenger_count
        FROM (
            SELECT passenger_id, COUNT(*) as bookings_per_passenger
            FROM booking
            GROUP BY passenger_id
        ) passenger_bookings
        GROUP BY bookings_per_passenger
        ORDER BY bookings_per_passenger DESC
        LIMIT 20
    """)
    
    distribution = session.exec(booking_distribution_query).all()
    
    if not distribution:
        print("   ❌ No bookings found in database")
        return False
    
    max_bookings = distribution[0].bookings_per_passenger
    
    if verbose:
        print(f"   Booking distribution (top 20):")
        for bookings, count in distribution:
            status = "✅" if bookings <= 100 else "❌"
            print(f"   {status} {bookings} booking(s): {count:,} passengers")
    
    # Check if any passenger exceeds 100 bookings
    over_limit_query = text("""
        SELECT COUNT(*) as passengers_over_limit
        FROM (
            SELECT passenger_id, COUNT(*) as bookings_per_passenger
            FROM booking
            GROUP BY passenger_id
            HAVING COUNT(*) > 100
        ) over_limit_passengers
    """)
    
    passengers_over_limit = session.exec(over_limit_query).first()
    
    if passengers_over_limit == 0:
        print(f"   ✅ Booking limit per passenger respected: max {max_bookings} bookings")
        return True
    else:
        print(f"   ❌ Booking limit exceeded by {passengers_over_limit} passenger(s)")
        print(f"      Highest: {max_bookings} bookings per passenger")
        return False


def validate_database_summary(session: Session, verbose: bool = False):
    """Show overall database summary"""
    print("\n📊 Database Summary:")
    
    # Get counts for all major tables
    flight_count = session.exec(select(func.count(Flight.flight_id))).first()
    passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
    booking_count = session.exec(select(func.count(Booking.booking_id))).first()
    
    print(f"   Flights: {flight_count:,}")
    print(f"   Passengers: {passenger_count:,}")
    print(f"   Bookings: {booking_count:,}")
    
    if flight_count > 0 and booking_count > 0:
        avg_bookings_per_flight = booking_count / flight_count
        print(f"   Average bookings per flight: {avg_bookings_per_flight:.1f}")
    
    if passenger_count > 0 and booking_count > 0:
        avg_bookings_per_passenger = booking_count / passenger_count
        print(f"   Average bookings per passenger: {avg_bookings_per_passenger:.1f}")
    
    # Date range summary
    if flight_count > 0:
        date_range_query = text("""
            SELECT 
                MIN(DATE(departure)) as start_date,
                MAX(DATE(departure)) as end_date,
                COUNT(DISTINCT DATE(departure)) as total_days
            FROM flight
            WHERE departure IS NOT NULL
        """)
        
        date_info = session.exec(date_range_query).first()
        if date_info:
            print(f"   Flight date range: {date_info.start_date} to {date_info.end_date}")
            print(f"   Total flight days: {date_info.total_days}")
            
            if date_info.total_days > 0:
                avg_flights_per_day = flight_count / date_info.total_days
                print(f"   Average flights per day: {avg_flights_per_day:.1f}")


def main():
    parser = argparse.ArgumentParser(description='Validate workshop database constraints')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output with detailed statistics')
    
    args = parser.parse_args()
    
    print("🔍 Workshop Constraints Validation")
    print("=" * 40)
    
    try:
        db_manager = DatabaseManager()
        
        with Session(db_manager.engine) as session:
            # Run all validations
            validations = [
                validate_flight_date_range(session, args.verbose),
                validate_daily_flight_limits(session, args.verbose),
                validate_passenger_count(session, args.verbose),
                validate_bookings_per_passenger(session, args.verbose)
            ]
            
            # Show database summary
            validate_database_summary(session, args.verbose)
            
            # Overall result
            all_valid = all(validations)
            
            print("\n" + "=" * 40)
            if all_valid:
                print("✅ All workshop constraints are satisfied!")
            else:
                failed_count = sum(1 for v in validations if not v)
                print(f"❌ {failed_count} constraint(s) failed validation")
                print("\nConstraint requirements:")
                print("  • Flights only in 2025 and first half of 2026")
                print("  • At most 1000 flights per day")
                print("  • Up to 1 million passengers")
                print("  • At most 100 bookings per passenger")
            
            return 0 if all_valid else 1
    
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return 1


if __name__ == "__main__":
    exit(main())