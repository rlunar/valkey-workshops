#!/usr/bin/env python3
"""
Optimized Booking Population Script for FlughafenDB

This script generates realistic booking data with improved performance:
- Streaming passenger selection instead of loading all into memory
- Simplified conflict detection for better performance
- Progress reporting every 100 flights
- Configurable limits for testing

Usage:
    python scripts/populate_bookings_optimized.py [--clear] [--max-flights 1000] [--verbose]
"""

import random
import argparse
import sys
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional
from decimal import Decimal
from sqlmodel import Session, select, text, func, and_, or_

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.booking import Booking
from models.flight import Flight
from models.passenger import Passenger
from models.airplane import Airplane


class OptimizedBookingPopulator:
    """Optimized booking populator with better performance"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.db_manager = DatabaseManager()
        
        # Booking patterns - Higher occupancy for realistic airline operations
        self.peak_occupancy_range = (0.90, 0.98)  # 90-98% during peak times
        self.off_peak_occupancy_range = (0.75, 0.88)  # 75-88% during off-peak
        
        # Business hours (6 AM - 10 PM local time)
        self.business_hours = (6, 22)
        
        # Peak travel days
        self.business_days = [0, 1, 2, 3]  # Mon-Thu
        self.leisure_days = [4, 5, 6]      # Fri-Sun
        
        # Seat class distribution
        self.seat_classes = {
            'economy': {'prefix': '', 'price_multiplier': 1.0, 'percentage': 85},
            'business': {'prefix': 'B', 'price_multiplier': 3.5, 'percentage': 12},
            'first': {'prefix': 'F', 'price_multiplier': 6.0, 'percentage': 3}
        }
        
        # Base pricing
        self.base_price_per_km = Decimal('0.15')
        
        # Cache passenger count for efficient random selection
        self.total_passengers = 0
        
        # Frequent flyer system - some passengers travel more often
        self.frequent_flyer_percentage = 0.15  # 15% of passengers are frequent flyers
        self.frequent_flyer_multiplier = 8     # They fly 8x more often
        self.regular_passenger_weight = 1      # Regular passengers base weight
        
        print(f"🎯 Optimized booking populator initialized")
        print(f"   📈 Peak occupancy: {self.peak_occupancy_range[0]*100:.0f}-{self.peak_occupancy_range[1]*100:.0f}%")
        print(f"   📉 Off-peak occupancy: {self.off_peak_occupancy_range[0]*100:.0f}-{self.off_peak_occupancy_range[1]*100:.0f}%")
        print(f"   ✈️  Frequent flyers: {self.frequent_flyer_percentage*100:.0f}% of passengers")
    
    def is_peak_time(self, departure: datetime) -> bool:
        """Determine if a flight departure is during peak travel time"""
        hour = departure.hour
        is_business_hours = self.business_hours[0] <= hour <= self.business_hours[1]
        
        weekday = departure.weekday()
        is_business_day = weekday in self.business_days
        
        # Simplified holiday detection
        month = departure.month
        day = departure.day
        is_holiday_period = (
            (month == 12 and day >= 20) or
            (month == 1 and day <= 5) or
            (month == 7 and 1 <= day <= 15) or
            (month == 11 and 20 <= day <= 30)
        )
        
        return (is_business_hours and is_business_day) or is_holiday_period
    
    def calculate_occupancy_rate(self, departure: datetime) -> float:
        """Calculate target occupancy rate based on flight timing"""
        if self.is_peak_time(departure):
            return random.uniform(*self.peak_occupancy_range)
        else:
            return random.uniform(*self.off_peak_occupancy_range)
    
    def generate_seat_assignment(self, capacity: int, seat_class: str, used_seats: Set[str]) -> Optional[str]:
        """Generate unique seat assignment with better success rate"""
        prefix = self.seat_classes[seat_class]['prefix']
        
        # Determine aircraft layout
        if capacity <= 50:
            max_row = max(1, capacity // 4)
            letters = ['A', 'B', 'C', 'D']
        elif capacity <= 150:
            max_row = max(1, capacity // 6)
            letters = ['A', 'B', 'C', 'D', 'E', 'F']
        else:
            max_row = max(1, capacity // 9)
            letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J']
        
        # Try to find an available seat (more attempts)
        for _ in range(25):
            row = random.randint(1, max_row)
            letter = random.choice(letters)
            seat = f"{prefix}{row}{letter}"
            
            if seat not in used_seats:
                return seat
        
        # If we still can't find a seat, try sequential assignment
        for row in range(1, max_row + 1):
            for letter in letters:
                seat = f"{prefix}{row}{letter}"
                if seat not in used_seats:
                    return seat
        
        return None  # Truly couldn't find a seat
    
    def calculate_price(self, seat_class: str, departure: datetime) -> Decimal:
        """Calculate ticket price"""
        # Simplified distance (could be enhanced with actual airport coordinates)
        base_distance = random.uniform(500, 3000)  # km
        base_price = Decimal(str(base_distance)) * self.base_price_per_km
        
        # Apply class multiplier
        class_multiplier = Decimal(str(self.seat_classes[seat_class]['price_multiplier']))
        price = base_price * class_multiplier
        
        # Peak time surcharge
        if self.is_peak_time(departure):
            price *= Decimal('1.25')  # 25% surcharge
        
        # Add variation
        variation = Decimal(str(random.uniform(0.8, 1.2)))
        price *= variation
        
        # Ensure minimum price
        return max(price.quantize(Decimal('0.01')), Decimal('50.00'))
    
    def get_random_passengers(self, session: Session, count: int) -> List[int]:
        """Get random passenger IDs with frequent flyer weighting"""
        if self.total_passengers == 0:
            self.total_passengers = session.exec(select(func.count(Passenger.passenger_id))).first()
        
        max_id = self.total_passengers
        selected_ids = []
        
        # Determine frequent flyer boundary (first 15% of passenger IDs are frequent flyers)
        frequent_flyer_boundary = int(max_id * self.frequent_flyer_percentage)
        
        for _ in range(count):
            # Weighted selection: frequent flyers are much more likely to be selected
            if random.random() < 0.55:  # 55% chance to select a frequent flyer
                # Select from frequent flyer pool (first 15% of passengers)
                passenger_id = random.randint(1, max(1, frequent_flyer_boundary))
            else:
                # Select from all passengers (including frequent flyers)
                passenger_id = random.randint(1, max_id)
            
            selected_ids.append(passenger_id)
        
        return selected_ids
    
    def populate_flight_bookings(self, session: Session, flight: Flight, capacity: int) -> List[Booking]:
        """Generate bookings for a single flight"""
        target_occupancy = self.calculate_occupancy_rate(flight.departure)
        target_passengers = int(capacity * target_occupancy)
        
        # Ensure minimum occupancy (at least 70% even for smallest flights)
        min_passengers = max(1, int(capacity * 0.70))
        target_passengers = max(target_passengers, min_passengers)
        
        # Don't exceed capacity
        target_passengers = min(target_passengers, capacity)
        
        if target_passengers == 0:
            return []
        
        # Get random passengers for this flight (allowing duplicates for frequent flyers)
        passenger_ids = self.get_random_passengers(session, target_passengers)
        
        # Determine seat class distribution
        economy_seats = int(target_passengers * 0.85)
        business_seats = int(target_passengers * 0.12)
        first_seats = target_passengers - economy_seats - business_seats
        
        seat_classes = (['economy'] * economy_seats + 
                       ['business'] * business_seats + 
                       ['first'] * first_seats)
        random.shuffle(seat_classes)
        
        bookings = []
        used_seats = set()
        successful_bookings = 0
        
        for i, passenger_id in enumerate(passenger_ids):
            if i >= len(seat_classes) or successful_bookings >= capacity:
                break
                
            seat_class = seat_classes[i]
            
            # Generate seat assignment with more attempts
            seat = self.generate_seat_assignment(capacity, seat_class, used_seats)
            if not seat:
                # If we can't find a seat in the preferred class, try economy
                if seat_class != 'economy':
                    seat = self.generate_seat_assignment(capacity, 'economy', used_seats)
                
                if not seat:
                    continue  # Skip if still no seat available
            
            used_seats.add(seat)
            
            # Calculate price
            price = self.calculate_price(seat_class, flight.departure)
            
            # Create booking
            booking = Booking(
                flight_id=flight.flight_id,
                seat=seat,
                passenger_id=passenger_id,
                price=price
            )
            bookings.append(booking)
            successful_bookings += 1
        
        return bookings


def populate_bookings_optimized(clear_existing: bool = False, max_flights: Optional[int] = None, 
                               batch_size: int = 5000, verbose: bool = False):
    """Optimized booking population function"""
    
    print(f"🚀 Starting OPTIMIZED booking population")
    print(f"   📋 Batch size: {batch_size:,}")
    if max_flights:
        print(f"   🎯 Max flights: {max_flights:,}")
    
    populator = OptimizedBookingPopulator(verbose=verbose)
    
    # Ensure tables exist
    populator.db_manager.create_tables()
    
    start_time = time.time()
    
    try:
        with Session(populator.db_manager.engine) as session:
            # Clear existing bookings if requested
            if clear_existing:
                print("   🗑️  Clearing existing bookings...")
                session.execute(text('DELETE FROM booking'))
                session.commit()
                print("   ✅ Existing bookings cleared")
            
            # Get flight and passenger counts
            flight_count = session.exec(select(func.count(Flight.flight_id))).first()
            passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
            
            print(f"   📊 Found {flight_count:,} flights and {passenger_count:,} passengers")
            
            if flight_count == 0 or passenger_count == 0:
                print("❌ No flights or passengers found. Please populate flights and passengers first.")
                return
            
            # Cache passenger count
            populator.total_passengers = passenger_count
            
            # Process flights in batches
            total_bookings = 0
            flights_processed = 0
            
            # Get flights with capacity, optionally limited
            flights_query = select(Flight, Airplane.capacity).join(
                Airplane, Flight.airplane_id == Airplane.airplane_id
            ).order_by(Flight.departure)
            
            if max_flights:
                flights_query = flights_query.limit(max_flights)
            
            batch_bookings = []
            last_progress_time = time.time()
            
            for flight, capacity in session.exec(flights_query):
                # Generate bookings for this flight
                flight_bookings = populator.populate_flight_bookings(session, flight, capacity)
                batch_bookings.extend(flight_bookings)
                flights_processed += 1
                
                # Progress reporting every 100 flights or 30 seconds
                current_time = time.time()
                if (flights_processed % 100 == 0 or 
                    current_time - last_progress_time > 30):
                    
                    elapsed = current_time - start_time
                    rate = flights_processed / elapsed if elapsed > 0 else 0
                    
                    print(f"   ⚡ Processed {flights_processed:,} flights, "
                          f"{len(batch_bookings):,} bookings queued ({rate:.1f} flights/sec)")
                    
                    last_progress_time = current_time
                
                # Process batch when it reaches target size
                if len(batch_bookings) >= batch_size:
                    try:
                        session.add_all(batch_bookings)
                        session.commit()
                        
                        total_bookings += len(batch_bookings)
                        
                        elapsed = time.time() - start_time
                        booking_rate = total_bookings / elapsed if elapsed > 0 else 0
                        
                        print(f"   💾 Committed batch: {total_bookings:,} total bookings "
                              f"({booking_rate:.0f} bookings/sec)")
                        
                        batch_bookings = []
                        
                    except Exception as e:
                        print(f"   ⚠️  Batch commit failed: {e}")
                        session.rollback()
                        
                        # Try to commit smaller chunks
                        chunk_size = len(batch_bookings) // 4
                        if chunk_size > 0:
                            print(f"   🔄 Retrying with smaller chunks ({chunk_size} bookings each)...")
                            for i in range(0, len(batch_bookings), chunk_size):
                                chunk = batch_bookings[i:i + chunk_size]
                                try:
                                    session.add_all(chunk)
                                    session.commit()
                                    total_bookings += len(chunk)
                                except Exception as chunk_error:
                                    print(f"   ❌ Chunk failed: {chunk_error}")
                                    session.rollback()
                        
                        batch_bookings = []
            
            # Process remaining bookings
            if batch_bookings:
                try:
                    session.add_all(batch_bookings)
                    session.commit()
                    total_bookings += len(batch_bookings)
                except Exception as e:
                    print(f"   ⚠️  Final batch commit failed: {e}")
                    session.rollback()
                    
                    # Try individual commits for remaining bookings
                    print(f"   🔄 Committing remaining {len(batch_bookings)} bookings individually...")
                    for booking in batch_bookings:
                        try:
                            session.add(booking)
                            session.commit()
                            total_bookings += 1
                        except Exception as individual_error:
                            session.rollback()
                            if verbose:
                                print(f"   ❌ Individual booking failed: {individual_error}")
            
            # Final statistics
            total_time = time.time() - start_time
            avg_flight_rate = flights_processed / total_time if total_time > 0 else 0
            avg_booking_rate = total_bookings / total_time if total_time > 0 else 0
            
            print(f"\n🎉 Optimized booking population completed!")
            print(f"   📈 Total bookings: {total_bookings:,}")
            print(f"   ✈️  Flights processed: {flights_processed:,}")
            print(f"   ⏱️  Total time: {total_time/60:.1f} minutes")
            print(f"   🚀 Flight rate: {avg_flight_rate:.1f} flights/second")
            print(f"   🚀 Booking rate: {avg_booking_rate:.0f} bookings/second")
            
            if total_bookings > 0:
                avg_bookings_per_flight = total_bookings / flights_processed
                print(f"   📊 Average bookings per flight: {avg_bookings_per_flight:.1f}")
    
    except Exception as e:
        print(f"❌ Database error during booking population: {e}")
        print("This might be due to:")
        print("  • Database connection timeout (try smaller batch sizes)")
        print("  • Memory issues (reduce --batch-size)")
        print("  • Transaction deadlocks (retry the operation)")
        print("\nSuggested fixes:")
        print("  • Retry with: --batch-size 1000")
        print("  • Or try: --max-flights 10000 (process fewer flights)")
        raise


def main():
    parser = argparse.ArgumentParser(description='Optimized booking population with better performance')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing booking data before starting')
    parser.add_argument('--max-flights', type=int,
                       help='Maximum number of flights to process (for testing)')
    parser.add_argument('--batch-size', type=int, default=5000,
                       help='Batch size for database operations (default: 5000)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.batch_size <= 0:
        print("❌ Error: batch-size must be positive")
        return 1
    
    if args.max_flights and args.max_flights <= 0:
        print("❌ Error: max-flights must be positive")
        return 1
    
    try:
        populate_bookings_optimized(args.clear, args.max_flights, args.batch_size, args.verbose)
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