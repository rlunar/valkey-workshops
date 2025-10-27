#!/usr/bin/env python3
"""
Limited Booking Population Script for FlughafenDB

This script generates realistic booking data with passenger booking limits:
- Maximum 100 bookings per passenger
- Streaming passenger selection for better performance
- Progress reporting and configurable limits

Usage:
    python scripts/populate_bookings_limited.py [--clear] [--max-flights 50000] [--max-bookings-per-passenger 100]
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
from collections import defaultdict

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.booking import Booking
from models.flight import Flight
from models.passenger import Passenger
from models.airplane import Airplane


class LimitedBookingPopulator:
    """Booking populator with per-passenger booking limits"""
    
    def __init__(self, max_bookings_per_passenger: int = 100, verbose: bool = False):
        self.verbose = verbose
        self.db_manager = DatabaseManager()
        self.max_bookings_per_passenger = max_bookings_per_passenger
        
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
        
        # Track passenger booking counts
        self.passenger_booking_counts = defaultdict(int)
        
        # Frequent flyer system - some passengers travel more often
        self.frequent_flyer_percentage = 0.15  # 15% of passengers are frequent flyers
        self.frequent_flyer_multiplier = 8     # They fly 8x more often
        self.regular_passenger_weight = 1      # Regular passengers base weight
        
        print(f"🎯 Limited booking populator initialized")
        print(f"   📈 Peak occupancy: {self.peak_occupancy_range[0]*100:.0f}-{self.peak_occupancy_range[1]*100:.0f}%")
        print(f"   📉 Off-peak occupancy: {self.off_peak_occupancy_range[0]*100:.0f}-{self.off_peak_occupancy_range[1]*100:.0f}%")
        print(f"   ✈️  Frequent flyers: {self.frequent_flyer_percentage*100:.0f}% of passengers")
        print(f"   🎫 Max bookings per passenger: {self.max_bookings_per_passenger}")
    
    def load_existing_booking_counts(self, session: Session):
        """Load existing booking counts for passengers"""
        if self.verbose:
            print("Loading existing passenger booking counts...")
        
        # Get current booking counts per passenger
        booking_counts_query = text("""
            SELECT passenger_id, COUNT(*) as booking_count
            FROM booking
            GROUP BY passenger_id
        """)
        
        results = session.exec(booking_counts_query).all()
        for passenger_id, count in results:
            self.passenger_booking_counts[passenger_id] = count
        
        if self.verbose:
            total_existing = sum(self.passenger_booking_counts.values())
            passengers_with_bookings = len(self.passenger_booking_counts)
            print(f"   Found {total_existing:,} existing bookings for {passengers_with_bookings:,} passengers")
    
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
    
    def calculate_price(self, seat_class: str, departure: datetime) -> Decimal:
        """Calculate ticket price based on seat class and timing"""
        # Base price (simplified - would normally use distance)
        base_price = Decimal('200.00')
        
        # Seat class multiplier
        class_info = self.seat_classes[seat_class]
        price = base_price * Decimal(str(class_info['price_multiplier']))
        
        # Peak time premium
        if self.is_peak_time(departure):
            price *= Decimal('1.3')
        
        # Add variation
        variation = Decimal(str(random.uniform(0.8, 1.2)))
        price *= variation
        
        # Ensure minimum price
        return max(price.quantize(Decimal('0.01')), Decimal('50.00'))
    
    def get_available_passengers(self, session: Session, count: int) -> List[int]:
        """Get random passenger IDs that haven't reached their booking limit"""
        if self.total_passengers == 0:
            self.total_passengers = session.exec(select(func.count(Passenger.passenger_id))).first()
        
        max_id = self.total_passengers
        selected_ids = []
        attempts = 0
        max_attempts = count * 10  # Prevent infinite loops
        
        # Determine frequent flyer boundary (first 15% of passenger IDs are frequent flyers)
        frequent_flyer_boundary = int(max_id * self.frequent_flyer_percentage)
        
        while len(selected_ids) < count and attempts < max_attempts:
            attempts += 1
            
            # Weighted selection: frequent flyers are much more likely to be selected
            if random.random() < 0.55:  # 55% chance to select a frequent flyer
                # Select from frequent flyer pool (first 15% of passengers)
                passenger_id = random.randint(1, max(1, frequent_flyer_boundary))
            else:
                # Select from all passengers (including frequent flyers)
                passenger_id = random.randint(1, max_id)
            
            # Check if passenger hasn't reached booking limit
            current_bookings = self.passenger_booking_counts.get(passenger_id, 0)
            if current_bookings < self.max_bookings_per_passenger:
                selected_ids.append(passenger_id)
                # Update the count immediately to prevent double-booking in same flight
                self.passenger_booking_counts[passenger_id] = current_bookings + 1
        
        if len(selected_ids) < count and self.verbose:
            print(f"   Warning: Could only find {len(selected_ids)} available passengers out of {count} requested")
        
        return selected_ids
    
    def generate_seat_assignment(self, capacity: int, seat_class: str, used_seats: Set[str]) -> Optional[str]:
        """Generate a seat assignment for the given class"""
        class_info = self.seat_classes[seat_class]
        prefix = class_info['prefix']
        
        # Estimate rows based on capacity
        rows = max(10, capacity // 6)  # Assume ~6 seats per row average
        
        # Try to find an available seat
        for _ in range(50):  # Max 50 attempts
            row = random.randint(1, rows)
            seat_letter = random.choice(['A', 'B', 'C', 'D', 'E', 'F'])
            seat = f"{prefix}{row}{seat_letter}"
            
            if seat not in used_seats:
                return seat
        
        return None  # No seat available
    
    def populate_flight_bookings(self, session: Session, flight: Flight, capacity: int) -> List[Booking]:
        """Generate bookings for a single flight with passenger limits"""
        target_occupancy = self.calculate_occupancy_rate(flight.departure)
        target_passengers = int(capacity * target_occupancy)
        
        # Ensure minimum occupancy (at least 70% even for smallest flights)
        min_passengers = max(1, int(capacity * 0.70))
        target_passengers = max(target_passengers, min_passengers)
        
        # Don't exceed capacity
        target_passengers = min(target_passengers, capacity)
        
        if target_passengers == 0:
            return []
        
        # Get available passengers for this flight (respecting booking limits)
        passenger_ids = self.get_available_passengers(session, target_passengers)
        
        if not passenger_ids:
            return []  # No available passengers
        
        # Determine seat class distribution
        actual_passengers = len(passenger_ids)
        economy_seats = int(actual_passengers * 0.85)
        business_seats = int(actual_passengers * 0.12)
        first_seats = actual_passengers - economy_seats - business_seats
        
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
            
            # Generate seat assignment
            seat = self.generate_seat_assignment(capacity, seat_class, used_seats)
            if not seat:
                # If we can't find a seat in the preferred class, try economy
                if seat_class != 'economy':
                    seat = self.generate_seat_assignment(capacity, 'economy', used_seats)
                
                if not seat:
                    # Revert the booking count since we couldn't create the booking
                    self.passenger_booking_counts[passenger_id] -= 1
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


def populate_bookings_limited(clear_existing: bool = False, max_flights: Optional[int] = None, 
                             max_bookings_per_passenger: int = 100, batch_size: int = 5000, 
                             verbose: bool = False):
    """Limited booking population function with per-passenger limits"""
    
    print(f"🎫 Starting limited booking population")
    print(f"   Max bookings per passenger: {max_bookings_per_passenger}")
    if max_flights:
        print(f"   Max flights to process: {max_flights:,}")
    
    populator = LimitedBookingPopulator(max_bookings_per_passenger, verbose)
    
    try:
        with Session(populator.db_manager.engine) as session:
            # Clear existing bookings if requested
            if clear_existing:
                if verbose:
                    print("Clearing existing bookings...")
                
                existing_count = session.exec(select(func.count(Booking.booking_id))).first()
                if existing_count > 0:
                    print(f"   Deleting {existing_count:,} existing bookings...")
                    session.exec(text("DELETE FROM booking"))
                    session.commit()
                    print(f"   ✅ Cleared {existing_count:,} bookings")
                else:
                    print("   No existing bookings to clear")
            else:
                # Load existing booking counts
                populator.load_existing_booking_counts(session)
            
            # Get flight and passenger counts
            flight_count = session.exec(select(func.count(Flight.flight_id))).first()
            passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
            
            print(f"   📊 Found {flight_count:,} flights and {passenger_count:,} passengers")
            
            if flight_count == 0:
                print("❌ No flights found. Please populate flights first.")
                return
            
            if passenger_count == 0:
                print("❌ No passengers found. Please populate passengers first.")
                return
            
            # Get flights to process
            flights_query = (
                select(Flight.flight_id, Flight.departure, Flight.airplane_id)
                .order_by(Flight.departure)
            )
            
            if max_flights:
                flights_query = flights_query.limit(max_flights)
            
            flights = session.exec(flights_query).all()
            
            if not flights:
                print("❌ No flights to process")
                return
            
            print(f"   🛫 Processing {len(flights):,} flights...")
            
            # Get aircraft capacities
            aircraft_capacities = {}
            aircraft_query = select(Airplane.airplane_id, Airplane.capacity)
            for airplane_id, capacity in session.exec(aircraft_query).all():
                aircraft_capacities[airplane_id] = capacity or 150  # Default capacity
            
            # Process flights in batches
            total_bookings = 0
            processed_flights = 0
            
            # Import tqdm for progress bar
            try:
                from tqdm import tqdm
                use_progress_bar = not verbose
            except ImportError:
                use_progress_bar = False
            
            if use_progress_bar:
                pbar = tqdm(
                    total=len(flights),
                    desc="🎫 Creating bookings",
                    unit="flight",
                    colour='green',
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} flights ({percentage:3.0f}%) [{elapsed}<{remaining}] {postfix}'
                )
            
            batch_bookings = []
            
            try:
                for flight_id, departure, airplane_id in flights:
                    capacity = aircraft_capacities.get(airplane_id, 150)
                    
                    # Create flight object for booking generation
                    flight = Flight(flight_id=flight_id, departure=departure, airplane_id=airplane_id)
                    
                    # Generate bookings for this flight
                    flight_bookings = populator.populate_flight_bookings(session, flight, capacity)
                    batch_bookings.extend(flight_bookings)
                    
                    processed_flights += 1
                    
                    # Insert in batches
                    if len(batch_bookings) >= batch_size:
                        session.add_all(batch_bookings)
                        session.commit()
                        total_bookings += len(batch_bookings)
                        batch_bookings = []
                    
                    # Update progress
                    if use_progress_bar:
                        pbar.update(1)
                        pbar.set_postfix({
                            'Bookings': f"{total_bookings:,}",
                            'Flight': len(flight_bookings)
                        })
                    elif verbose and processed_flights % 100 == 0:
                        print(f"   Processed {processed_flights:,}/{len(flights):,} flights, "
                              f"{total_bookings:,} bookings created")
                
                # Insert remaining bookings
                if batch_bookings:
                    session.add_all(batch_bookings)
                    session.commit()
                    total_bookings += len(batch_bookings)
                
                if use_progress_bar:
                    pbar.close()
                
                print(f"✅ Booking population completed!")
                print(f"   Processed flights: {processed_flights:,}")
                print(f"   Total bookings created: {total_bookings:,}")
                
                # Show passenger booking distribution
                if verbose:
                    booking_distribution = defaultdict(int)
                    for count in populator.passenger_booking_counts.values():
                        booking_distribution[min(count, 10)] += 1  # Cap at 10 for display
                    
                    print(f"\n   Passenger booking distribution:")
                    for bookings, passengers in sorted(booking_distribution.items()):
                        if bookings == 10:
                            print(f"   10+ bookings: {passengers:,} passengers")
                        else:
                            print(f"   {bookings} booking(s): {passengers:,} passengers")
                
            except KeyboardInterrupt:
                if use_progress_bar:
                    pbar.close()
                print(f"\n⚠ Booking population interrupted by user")
                print(f"   Processed {processed_flights:,} flights")
                print(f"   Created {total_bookings:,} bookings")
            except Exception as e:
                if use_progress_bar:
                    pbar.close()
                print(f"\n❌ Error during booking population: {e}")
                raise
    
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("\nSuggested fixes:")
        print("  • Retry with: --batch-size 1000")
        print("  • Or try: --max-flights 10000 (process fewer flights)")
        raise


def main():
    parser = argparse.ArgumentParser(description='Limited booking population with per-passenger limits')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing booking data before starting')
    parser.add_argument('--max-flights', type=int,
                       help='Maximum number of flights to process (for testing)')
    parser.add_argument('--max-bookings-per-passenger', type=int, default=100,
                       help='Maximum bookings per passenger (default: 100)')
    parser.add_argument('--batch-size', type=int, default=5000,
                       help='Batch size for database operations (default: 5000)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.max_flights and args.max_flights <= 0:
        print("❌ Error: max-flights must be positive")
        return 1
    
    if args.max_bookings_per_passenger <= 0:
        print("❌ Error: max-bookings-per-passenger must be positive")
        return 1
    
    if args.batch_size <= 0:
        print("❌ Error: batch-size must be positive")
        return 1
    
    try:
        populate_bookings_limited(
            clear_existing=args.clear,
            max_flights=args.max_flights,
            max_bookings_per_passenger=args.max_bookings_per_passenger,
            batch_size=args.batch_size,
            verbose=args.verbose
        )
        return 0
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())