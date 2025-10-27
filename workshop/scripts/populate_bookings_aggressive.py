#!/usr/bin/env python3
"""
Aggressive Booking Population Script for FlughafenDB

This script ensures flights are properly filled with passengers:
- Target: 100+ passengers per flight on average
- Fill flights to 90-100% capacity consistently
- Allow passenger duplicates across flights
- Simple, fast processing

Usage:
    python scripts/populate_bookings_aggressive.py [--clear] [--batch-size 10000] [--verbose]
"""

import random
import argparse
import sys
import os
import time
from datetime import datetime
from typing import List, Set
from decimal import Decimal
from sqlmodel import Session, select, text, func

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.booking import Booking
from models.flight import Flight
from models.passenger import Passenger
from models.airplane import Airplane


class AggressiveBookingPopulator:
    """Aggressive booking populator that fills flights to capacity"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.db_manager = DatabaseManager()
        
        # Very aggressive occupancy rates
        self.min_occupancy = 0.90  # 90% minimum
        self.max_occupancy = 1.00  # 100% maximum
        
        # Simplified pricing
        self.base_price = Decimal('200.00')
        self.price_variation = 0.5  # ±50% variation
        
        print(f"🎯 Aggressive booking populator initialized")
        print(f"   📊 Target occupancy: {self.min_occupancy*100:.0f}%-{self.max_occupancy*100:.0f}%")
        print(f"   🎯 Goal: Fill every flight to near capacity")
    
    def calculate_target_passengers(self, capacity: int) -> int:
        """Calculate target passengers - always high occupancy"""
        # Random occupancy between 90-100%
        occupancy = random.uniform(self.min_occupancy, self.max_occupancy)
        target = int(capacity * occupancy)
        
        # Ensure we always have at least 90% occupancy
        min_passengers = int(capacity * 0.90)
        return max(min_passengers, min(target, capacity))
    
    def generate_simple_seat(self, seat_number: int, capacity: int) -> str:
        """Generate simple seat assignment"""
        # Simple row/letter assignment
        if capacity <= 100:
            # Small/medium aircraft: 6 across (A-F)
            row = (seat_number // 6) + 1
            letter = ['A', 'B', 'C', 'D', 'E', 'F'][seat_number % 6]
        else:
            # Large aircraft: 9 across (A-J, skip I)
            row = (seat_number // 9) + 1
            letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J']
            letter = letters[seat_number % 9]
        
        return f"{row}{letter}"
    
    def calculate_simple_price(self) -> Decimal:
        """Calculate simple ticket price with variation"""
        variation = random.uniform(1 - self.price_variation, 1 + self.price_variation)
        price = self.base_price * Decimal(str(variation))
        return price.quantize(Decimal('0.01'))
    
    def populate_flight_bookings(self, flight: Flight, capacity: int, passenger_count: int) -> List[Booking]:
        """Generate bookings for a single flight - fill it up!"""
        target_passengers = self.calculate_target_passengers(capacity)
        
        if target_passengers == 0 or passenger_count == 0:
            return []
        
        bookings = []
        
        # Generate passengers for each seat
        for seat_num in range(target_passengers):
            # Random passenger (allowing duplicates)
            passenger_id = random.randint(1, passenger_count)
            
            # Simple seat assignment
            seat = self.generate_simple_seat(seat_num, capacity)
            
            # Simple price
            price = self.calculate_simple_price()
            
            booking = Booking(
                flight_id=flight.flight_id,
                seat=seat,
                passenger_id=passenger_id,
                price=price
            )
            bookings.append(booking)
        
        return bookings


def populate_bookings_aggressive(clear_existing: bool = False, batch_size: int = 10000, verbose: bool = False):
    """Main aggressive booking population function"""
    
    print(f"🚀 Starting AGGRESSIVE booking population")
    print(f"   📋 Batch size: {batch_size:,}")
    print(f"   🎯 Strategy: Fill every flight to 90-100% capacity")
    
    populator = AggressiveBookingPopulator(verbose=verbose)
    
    # Ensure tables exist
    populator.db_manager.create_tables()
    
    start_time = time.time()
    
    with Session(populator.db_manager.engine) as session:
        # Clear existing bookings if requested
        if clear_existing:
            print("   🗑️  Clearing existing bookings...")
            session.execute(text('DELETE FROM booking'))
            session.commit()
            print("   ✅ Existing bookings cleared")
        
        # Get counts
        flight_count = session.exec(select(func.count(Flight.flight_id))).first()
        passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
        
        # Get capacity statistics
        capacity_stats = session.exec(
            select(
                func.avg(Airplane.capacity).label('avg_capacity'),
                func.sum(Airplane.capacity).label('total_capacity')
            )
            .select_from(Flight)
            .join(Airplane, Flight.airplane_id == Airplane.airplane_id)
        ).first()
        
        print(f"   📊 Found {flight_count:,} flights and {passenger_count:,} passengers")
        print(f"   ✈️  Average aircraft capacity: {float(capacity_stats.avg_capacity):.1f} seats")
        print(f"   🏢 Total flight capacity: {capacity_stats.total_capacity:,} seats")
        
        if flight_count == 0 or passenger_count == 0:
            print("❌ No flights or passengers found. Please populate flights and passengers first.")
            return
        
        # Estimate target bookings
        estimated_bookings = int(float(capacity_stats.total_capacity) * 0.95)  # 95% occupancy target
        print(f"   🎯 Target bookings: ~{estimated_bookings:,} (95% occupancy)")
        
        # Process flights in batches
        total_bookings = 0
        flights_processed = 0
        total_capacity_processed = 0
        
        # Get flights with capacity
        flights_query = select(Flight, Airplane.capacity).join(
            Airplane, Flight.airplane_id == Airplane.airplane_id
        ).order_by(Flight.flight_id)  # Order by ID for consistent processing
        
        batch_bookings = []
        last_report_time = time.time()
        
        for flight, capacity in session.exec(flights_query):
            # Generate bookings for this flight
            flight_bookings = populator.populate_flight_bookings(flight, capacity, passenger_count)
            
            batch_bookings.extend(flight_bookings)
            flights_processed += 1
            total_capacity_processed += capacity
            
            # Progress reporting every 1000 flights or 30 seconds
            current_time = time.time()
            if (flights_processed % 1000 == 0 or 
                current_time - last_report_time > 30):
                
                elapsed = current_time - start_time
                flight_rate = flights_processed / elapsed if elapsed > 0 else 0
                current_bookings = len(batch_bookings) + total_bookings
                current_occupancy = (current_bookings / total_capacity_processed * 100) if total_capacity_processed > 0 else 0
                avg_per_flight = current_bookings / flights_processed if flights_processed > 0 else 0
                
                print(f"   ⚡ Processed {flights_processed:,}/{flight_count:,} flights")
                print(f"      📈 {current_bookings:,} bookings ({current_occupancy:.1f}% occupancy)")
                print(f"      👥 {avg_per_flight:.1f} passengers per flight")
                print(f"      🚀 {flight_rate:.1f} flights/sec")
                
                last_report_time = current_time
            
            # Process batch when it reaches target size
            if len(batch_bookings) >= batch_size:
                try:
                    session.add_all(batch_bookings)
                    session.commit()
                    
                    total_bookings += len(batch_bookings)
                    batch_bookings = []
                    
                    if verbose:
                        elapsed = time.time() - start_time
                        booking_rate = total_bookings / elapsed if elapsed > 0 else 0
                        print(f"   💾 Committed batch: {total_bookings:,} total bookings ({booking_rate:.0f} bookings/sec)")
                
                except Exception as e:
                    print(f"   ❌ Batch commit failed: {e}")
                    session.rollback()
                    batch_bookings = []
        
        # Process remaining bookings
        if batch_bookings:
            try:
                session.add_all(batch_bookings)
                session.commit()
                total_bookings += len(batch_bookings)
            except Exception as e:
                print(f"   ❌ Final batch commit failed: {e}")
                session.rollback()
        
        # Final statistics
        total_time = time.time() - start_time
        avg_flight_rate = flights_processed / total_time if total_time > 0 else 0
        avg_booking_rate = total_bookings / total_time if total_time > 0 else 0
        avg_occupancy = (total_bookings / total_capacity_processed * 100) if total_capacity_processed > 0 else 0
        avg_passengers_per_flight = total_bookings / flights_processed if flights_processed > 0 else 0
        
        print(f"\n🎉 Aggressive booking population completed!")
        print(f"   📈 Total bookings: {total_bookings:,}")
        print(f"   ✈️  Flights processed: {flights_processed:,}")
        print(f"   🏢 Total capacity processed: {total_capacity_processed:,} seats")
        print(f"   📊 Overall occupancy: {avg_occupancy:.1f}%")
        print(f"   👥 Average passengers per flight: {avg_passengers_per_flight:.1f}")
        print(f"   ⏱️  Total time: {total_time/60:.1f} minutes")
        print(f"   🚀 Processing rate: {avg_flight_rate:.1f} flights/sec, {avg_booking_rate:.0f} bookings/sec")
        
        # Success metrics
        if avg_passengers_per_flight >= 100:
            print(f"   ✅ SUCCESS: Achieved {avg_passengers_per_flight:.1f} passengers per flight!")
        elif avg_passengers_per_flight >= 80:
            print(f"   🟡 CLOSE: {avg_passengers_per_flight:.1f} passengers per flight (target: 100+)")
        else:
            print(f"   ❌ NEEDS WORK: {avg_passengers_per_flight:.1f} passengers per flight (target: 100+)")
        
        if avg_occupancy >= 90:
            print(f"   ✅ EXCELLENT: {avg_occupancy:.1f}% occupancy rate")
        elif avg_occupancy >= 80:
            print(f"   🟡 GOOD: {avg_occupancy:.1f}% occupancy rate")
        else:
            print(f"   ❌ LOW: {avg_occupancy:.1f}% occupancy rate")


def main():
    parser = argparse.ArgumentParser(description='Aggressive booking population for maximum occupancy')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing booking data before starting')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Batch size for database operations (default: 10000)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.batch_size <= 0:
        print("❌ Error: batch-size must be positive")
        return 1
    
    try:
        populate_bookings_aggressive(args.clear, args.batch_size, args.verbose)
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())