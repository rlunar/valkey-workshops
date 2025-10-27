#!/usr/bin/env python3
"""
Simplified Booking Population Script for FlughafenDB

This script generates booking data with high occupancy rates:
- Target 90% average occupancy across all flights
- Some flights at 100% capacity (peak times)
- Passengers can be on multiple flights (no conflict checking)
- Simplified seat assignment and pricing
- Focus on filling flights rather than realistic passenger behavior

Usage:
    python scripts/populate_bookings_simple.py [--clear] [--batch-size 10000] [--verbose]
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


class SimpleBookingPopulator:
    """Simplified booking populator focused on high occupancy"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.db_manager = DatabaseManager()
        
        # Target occupancy rates - very high for maximum passengers per flight
        self.min_occupancy = 0.85  # 85% minimum
        self.avg_occupancy = 0.95  # 95% average target
        self.max_occupancy = 1.00  # 100% for peak flights
        
        # Seat class distribution (simplified)
        self.seat_classes = ['economy', 'business', 'first']
        self.class_weights = [85, 12, 3]  # Percentage distribution
        
        # Base pricing
        self.base_prices = {
            'economy': Decimal('150.00'),
            'business': Decimal('450.00'),
            'first': Decimal('900.00')
        }
        
        print(f"🎯 Simple booking populator initialized")
        print(f"   📊 Target occupancy: {self.min_occupancy*100:.0f}%-{self.max_occupancy*100:.0f}% (avg {self.avg_occupancy*100:.0f}%)")
        print(f"   🎯 Goal: 100+ passengers per flight on average")
    
    def calculate_target_passengers(self, capacity: int, departure: datetime) -> int:
        """Calculate how many passengers this flight should have"""
        # Peak times (business hours on weekdays) get higher occupancy
        hour = departure.hour
        weekday = departure.weekday()
        
        is_peak = (6 <= hour <= 22) and (weekday < 5)  # Business hours on weekdays
        
        if is_peak:
            # Peak flights: 95-100% occupancy (nearly full)
            occupancy = random.uniform(0.95, 1.00)
        else:
            # Off-peak flights: 85-98% occupancy (still very full)
            occupancy = random.uniform(0.85, 0.98)
        
        target = int(capacity * occupancy)
        
        # Ensure minimum passengers - at least 80% even for smallest aircraft
        min_passengers = max(int(capacity * 0.80), 1)
        return max(min_passengers, min(target, capacity))
    
    def generate_seat_assignment(self, capacity: int, seat_class: str, used_seats: Set[str]) -> str:
        """Generate a seat assignment (simplified)"""
        # Simple seat numbering based on capacity
        if capacity <= 50:
            # Small aircraft: 1-4 across, A-D
            max_row = (capacity + 3) // 4
            letters = ['A', 'B', 'C', 'D']
        elif capacity <= 150:
            # Medium aircraft: 1-6 across, A-F
            max_row = (capacity + 5) // 6
            letters = ['A', 'B', 'C', 'D', 'E', 'F']
        else:
            # Large aircraft: 1-9 across, A-J (skip I)
            max_row = (capacity + 8) // 9
            letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J']
        
        # Class prefixes
        prefix = {'economy': '', 'business': 'B', 'first': 'F'}.get(seat_class, '')
        
        # Try to find an available seat
        for attempt in range(50):  # Prevent infinite loops
            row = random.randint(1, max_row)
            letter = random.choice(letters)
            seat = f"{prefix}{row}{letter}"
            
            if seat not in used_seats:
                return seat
        
        # Fallback: sequential assignment
        for row in range(1, max_row + 1):
            for letter in letters:
                seat = f"{prefix}{row}{letter}"
                if seat not in used_seats:
                    return seat
        
        # Last resort: add a suffix to make it unique
        return f"{prefix}1A-{len(used_seats)}"
    
    def calculate_price(self, seat_class: str, departure: datetime) -> Decimal:
        """Calculate ticket price (simplified)"""
        base_price = self.base_prices[seat_class]
        
        # Add some variation (±30%)
        variation = Decimal(str(random.uniform(0.7, 1.3)))
        price = base_price * variation
        
        # Peak time surcharge (20%)
        hour = departure.hour
        weekday = departure.weekday()
        if (6 <= hour <= 22) and (weekday < 5):
            price *= Decimal('1.2')
        
        return price.quantize(Decimal('0.01'))
    
    def get_random_passengers(self, count: int, total_passengers: int) -> List[int]:
        """Get random passenger IDs (allowing duplicates)"""
        return [random.randint(1, total_passengers) for _ in range(count)]
    
    def populate_flight_bookings(self, flight: Flight, capacity: int, total_passengers: int) -> List[Booking]:
        """Generate bookings for a single flight"""
        target_passengers = self.calculate_target_passengers(capacity, flight.departure)
        
        if target_passengers == 0:
            return []
        
        # Get random passengers (duplicates allowed - frequent flyers!)
        passenger_ids = self.get_random_passengers(target_passengers, total_passengers)
        
        # Assign seat classes based on distribution
        seat_classes = []
        for class_name, weight in zip(self.seat_classes, self.class_weights):
            class_count = int(target_passengers * weight / 100)
            seat_classes.extend([class_name] * class_count)
        
        # Fill remaining seats with economy
        while len(seat_classes) < target_passengers:
            seat_classes.append('economy')
        
        # Shuffle for randomness
        random.shuffle(seat_classes)
        
        # Generate bookings
        bookings = []
        used_seats = set()
        
        for i, passenger_id in enumerate(passenger_ids):
            if i >= len(seat_classes):
                break
                
            seat_class = seat_classes[i]
            seat = self.generate_seat_assignment(capacity, seat_class, used_seats)
            used_seats.add(seat)
            
            price = self.calculate_price(seat_class, flight.departure)
            
            booking = Booking(
                flight_id=flight.flight_id,
                seat=seat,
                passenger_id=passenger_id,
                price=price
            )
            bookings.append(booking)
        
        return bookings


def populate_bookings_simple(clear_existing: bool = False, batch_size: int = 10000, verbose: bool = False):
    """Main simplified booking population function"""
    
    print(f"🚀 Starting SIMPLIFIED booking population")
    print(f"   📋 Batch size: {batch_size:,}")
    print(f"   🎯 Goal: ~90% average occupancy with high passenger counts")
    
    populator = SimpleBookingPopulator(verbose=verbose)
    
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
        
        print(f"   📊 Found {flight_count:,} flights and {passenger_count:,} passengers")
        
        if flight_count == 0 or passenger_count == 0:
            print("❌ No flights or passengers found. Please populate flights and passengers first.")
            return
        
        # Process flights in batches
        total_bookings = 0
        flights_processed = 0
        total_capacity = 0
        
        # Get flights with capacity
        flights_query = select(Flight, Airplane.capacity).join(
            Airplane, Flight.airplane_id == Airplane.airplane_id
        ).order_by(Flight.departure)
        
        batch_bookings = []
        
        for flight, capacity in session.exec(flights_query):
            # Generate bookings for this flight
            flight_bookings = populator.populate_flight_bookings(flight, capacity, passenger_count)
            
            batch_bookings.extend(flight_bookings)
            flights_processed += 1
            total_capacity += capacity
            
            # Progress reporting
            if flights_processed % 1000 == 0:
                elapsed = time.time() - start_time
                rate = flights_processed / elapsed if elapsed > 0 else 0
                current_bookings = len(batch_bookings) + total_bookings
                current_occupancy = (current_bookings / total_capacity * 100) if total_capacity > 0 else 0
                
                print(f"   ⚡ Processed {flights_processed:,} flights, "
                      f"{current_bookings:,} bookings ({current_occupancy:.1f}% occupancy, {rate:.1f} flights/sec)")
            
            # Process batch when it reaches target size
            if len(batch_bookings) >= batch_size:
                session.add_all(batch_bookings)
                session.commit()
                
                total_bookings += len(batch_bookings)
                batch_bookings = []
                
                if verbose:
                    elapsed = time.time() - start_time
                    booking_rate = total_bookings / elapsed if elapsed > 0 else 0
                    print(f"   💾 Committed batch: {total_bookings:,} total bookings ({booking_rate:.0f} bookings/sec)")
        
        # Process remaining bookings
        if batch_bookings:
            session.add_all(batch_bookings)
            session.commit()
            total_bookings += len(batch_bookings)
        
        # Final statistics
        total_time = time.time() - start_time
        avg_flight_rate = flights_processed / total_time if total_time > 0 else 0
        avg_booking_rate = total_bookings / total_time if total_time > 0 else 0
        avg_occupancy = (total_bookings / total_capacity * 100) if total_capacity > 0 else 0
        avg_passengers_per_flight = total_bookings / flights_processed if flights_processed > 0 else 0
        
        print(f"\n🎉 Simplified booking population completed!")
        print(f"   📈 Total bookings: {total_bookings:,}")
        print(f"   ✈️  Flights processed: {flights_processed:,}")
        print(f"   🏢 Total capacity: {total_capacity:,} seats")
        print(f"   📊 Overall occupancy: {avg_occupancy:.1f}%")
        print(f"   👥 Average passengers per flight: {avg_passengers_per_flight:.1f}")
        print(f"   ⏱️  Total time: {total_time/60:.1f} minutes")
        print(f"   🚀 Processing rate: {avg_flight_rate:.1f} flights/sec, {avg_booking_rate:.0f} bookings/sec")
        
        # Verify the results match expectations
        if avg_passengers_per_flight >= 100:
            print(f"   ✅ SUCCESS: Achieved {avg_passengers_per_flight:.1f} passengers per flight (target: 100+)")
        elif avg_passengers_per_flight >= 50:
            print(f"   ⚠️  Getting closer: {avg_passengers_per_flight:.1f} passengers per flight (target: 100+)")
        else:
            print(f"   ❌ Still too low: {avg_passengers_per_flight:.1f} passengers per flight (target: 100+)")
            print(f"   💡 Check if aircraft capacities are realistic (should be 100-400+ seats for commercial flights)")


def main():
    parser = argparse.ArgumentParser(description='Simplified booking population for high occupancy')
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
        populate_bookings_simple(args.clear, args.batch_size, args.verbose)
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