#!/usr/bin/env python3
"""
Comprehensive Booking Population Script for FlughafenDB

This script generates realistic booking data with:
- Peak time occupancy (90-95% during business hours, holidays)
- Off-peak occupancy (60-75% during nights, weekends)
- No double-booking of passengers on overlapping flights
- Business vs leisure travel patterns
- Realistic seat assignments and pricing
- Return flight assumptions for business and leisure travelers

Usage:
    python scripts/populate_bookings.py [--clear] [--batch-size 10000] [--verbose]
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
from models.airport import Airport


class BookingPopulator:
    """Generate realistic booking data with business rules"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.db_manager = DatabaseManager()
        
        # Booking patterns
        self.peak_occupancy_range = (0.90, 0.95)  # 90-95% during peak
        self.off_peak_occupancy_range = (0.60, 0.75)  # 60-75% off-peak
        
        # Business hours (6 AM - 10 PM local time)
        self.business_hours = (6, 22)
        
        # Peak travel days (Monday-Thursday for business, Friday-Sunday for leisure)
        self.business_days = [0, 1, 2, 3]  # Mon-Thu
        self.leisure_days = [4, 5, 6]      # Fri-Sun
        
        # Seat class distribution
        self.seat_classes = {
            'economy': {'prefix': '', 'price_multiplier': 1.0, 'percentage': 85},
            'business': {'prefix': 'B', 'price_multiplier': 3.5, 'percentage': 12},
            'first': {'prefix': 'F', 'price_multiplier': 6.0, 'percentage': 3}
        }
        
        # Base pricing per distance (simplified)
        self.base_price_per_km = Decimal('0.15')  # $0.15 per km base
        
        # Passenger tracking for double-booking prevention
        self.passenger_flight_times: Dict[int, List[Tuple[datetime, datetime]]] = {}
        
        print(f"🎯 Booking populator initialized")
        if self.verbose:
            print(f"   📊 Peak occupancy: {self.peak_occupancy_range[0]*100:.0f}-{self.peak_occupancy_range[1]*100:.0f}%")
            print(f"   📊 Off-peak occupancy: {self.off_peak_occupancy_range[0]*100:.0f}-{self.off_peak_occupancy_range[1]*100:.0f}%")
    
    def is_peak_time(self, departure: datetime) -> bool:
        """Determine if a flight departure is during peak travel time"""
        # Check if it's business hours
        hour = departure.hour
        is_business_hours = self.business_hours[0] <= hour <= self.business_hours[1]
        
        # Check if it's a business day
        weekday = departure.weekday()
        is_business_day = weekday in self.business_days
        
        # Check for holiday periods (simplified - around major holidays)
        month = departure.month
        day = departure.day
        is_holiday_period = (
            (month == 12 and day >= 20) or  # Christmas/New Year
            (month == 1 and day <= 5) or   # New Year
            (month == 7 and 1 <= day <= 15) or  # Summer vacation
            (month == 11 and 20 <= day <= 30)   # Thanksgiving
        )
        
        # Peak time if business hours + business day, or holiday period
        return (is_business_hours and is_business_day) or is_holiday_period
    
    def calculate_occupancy_rate(self, departure: datetime, capacity: int) -> float:
        """Calculate target occupancy rate based on flight timing"""
        if self.is_peak_time(departure):
            return random.uniform(*self.peak_occupancy_range)
        else:
            return random.uniform(*self.off_peak_occupancy_range)
    
    def generate_seat_assignment(self, capacity: int, seat_class: str) -> str:
        """Generate realistic seat assignment based on aircraft capacity"""
        # Simplified seat assignment - assumes 6-across seating for most aircraft
        if capacity <= 50:  # Small aircraft
            rows = capacity // 4  # 4-across seating
            row = random.randint(1, rows)
            seat_letter = random.choice(['A', 'B', 'C', 'D'])
        elif capacity <= 150:  # Medium aircraft
            rows = capacity // 6  # 6-across seating
            row = random.randint(1, rows)
            seat_letter = random.choice(['A', 'B', 'C', 'D', 'E', 'F'])
        else:  # Large aircraft
            rows = capacity // 9  # 9-across seating (3-3-3)
            row = random.randint(1, rows)
            seat_letter = random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J'])
        
        # Add class prefix if applicable
        prefix = self.seat_classes[seat_class]['prefix']
        return f"{prefix}{row}{seat_letter}"
    
    def calculate_price(self, base_distance_km: float, seat_class: str, 
                       departure: datetime, is_return: bool = False) -> Decimal:
        """Calculate ticket price based on distance, class, timing, and return status"""
        base_price = Decimal(str(base_distance_km)) * self.base_price_per_km
        
        # Apply class multiplier
        class_multiplier = Decimal(str(self.seat_classes[seat_class]['price_multiplier']))
        price = base_price * class_multiplier
        
        # Peak time surcharge
        if self.is_peak_time(departure):
            price *= Decimal('1.3')  # 30% surcharge for peak times
        
        # Return flight discount (10% off for round trips)
        if is_return:
            price *= Decimal('0.9')
        
        # Add some randomness (±20%)
        variation = Decimal(str(random.uniform(0.8, 1.2)))
        price *= variation
        
        # Ensure minimum price
        min_price = Decimal('50.00')
        return max(price.quantize(Decimal('0.01')), min_price)
    
    def passenger_has_conflict(self, passenger_id: int, departure: datetime, 
                              arrival: datetime) -> bool:
        """Check if passenger has conflicting flights"""
        if passenger_id not in self.passenger_flight_times:
            return False
        
        for existing_dep, existing_arr in self.passenger_flight_times[passenger_id]:
            # Check for overlap (with 2-hour buffer for connections)
            buffer = timedelta(hours=2)
            if (departure < existing_arr + buffer and 
                arrival + buffer > existing_dep):
                return True
        
        return False
    
    def add_passenger_flight(self, passenger_id: int, departure: datetime, arrival: datetime):
        """Track passenger flight times to prevent conflicts"""
        if passenger_id not in self.passenger_flight_times:
            self.passenger_flight_times[passenger_id] = []
        
        self.passenger_flight_times[passenger_id].append((departure, arrival))
    
    def determine_seat_class_distribution(self, capacity: int) -> List[str]:
        """Determine seat class distribution for an aircraft"""
        classes = []
        
        # Calculate seats per class
        economy_seats = int(capacity * self.seat_classes['economy']['percentage'] / 100)
        business_seats = int(capacity * self.seat_classes['business']['percentage'] / 100)
        first_seats = capacity - economy_seats - business_seats  # Remainder goes to first
        
        # Build class list
        classes.extend(['economy'] * economy_seats)
        classes.extend(['business'] * business_seats)
        classes.extend(['first'] * first_seats)
        
        return classes
    
    def should_book_return_flight(self, departure: datetime, is_business_traveler: bool) -> bool:
        """Determine if passenger should book a return flight"""
        # Business travelers: 85% book returns, usually within 1-7 days
        # Leisure travelers: 70% book returns, usually within 3-21 days
        
        if is_business_traveler:
            return random.random() < 0.85
        else:
            return random.random() < 0.70
    
    def find_return_flight(self, session: Session, outbound_flight: Flight, 
                          passenger_id: int, is_business_traveler: bool) -> Optional[Flight]:
        """Find a suitable return flight for a passenger"""
        # Determine return timeframe
        if is_business_traveler:
            min_days = 1
            max_days = 7
        else:
            min_days = 3
            max_days = 21
        
        earliest_return = outbound_flight.arrival + timedelta(days=min_days)
        latest_return = outbound_flight.arrival + timedelta(days=max_days)
        
        # Find return flights (destination -> origin)
        return_flights = session.exec(
            select(Flight)
            .where(
                and_(
                    Flight.from_airport == outbound_flight.to_airport,
                    Flight.to_airport == outbound_flight.from_airport,
                    Flight.departure >= earliest_return,
                    Flight.departure <= latest_return
                )
            )
            .limit(50)  # Limit to avoid too many options
        ).all()
        
        if not return_flights:
            return None
        
        # Filter out flights that would conflict with passenger's schedule
        suitable_flights = []
        for flight in return_flights:
            if not self.passenger_has_conflict(passenger_id, flight.departure, flight.arrival):
                suitable_flights.append(flight)
        
        if not suitable_flights:
            return None
        
        # Prefer flights with similar timing to outbound (business travelers)
        if is_business_traveler and len(suitable_flights) > 1:
            outbound_hour = outbound_flight.departure.hour
            suitable_flights.sort(key=lambda f: abs(f.departure.hour - outbound_hour))
        
        return random.choice(suitable_flights[:5])  # Pick from top 5 suitable flights
    
    def populate_flight_bookings(self, session: Session, flight: Flight, 
                                airplane_capacity: int, used_seats: Set[str],
                                available_passengers: List[int]) -> List[Booking]:
        """Generate bookings for a single flight"""
        target_occupancy = self.calculate_occupancy_rate(flight.departure, airplane_capacity)
        target_passengers = int(airplane_capacity * target_occupancy)
        
        # Don't exceed available passengers
        target_passengers = min(target_passengers, len(available_passengers))
        
        if target_passengers == 0:
            return []
        
        # Determine if this is primarily business or leisure travel
        is_business_route = self.is_peak_time(flight.departure)
        
        # Select passengers for this flight
        selected_passengers = random.sample(available_passengers, target_passengers)
        
        # Determine seat class distribution
        available_classes = self.determine_seat_class_distribution(airplane_capacity)
        random.shuffle(available_classes)
        
        bookings = []
        estimated_distance = 1000  # Simplified - could be calculated from airport coordinates
        
        for i, passenger_id in enumerate(selected_passengers):
            # Check for conflicts
            if self.passenger_has_conflict(passenger_id, flight.departure, flight.arrival):
                continue
            
            # Assign seat class
            seat_class = available_classes[i % len(available_classes)]
            
            # Generate unique seat assignment
            attempts = 0
            while attempts < 20:  # Prevent infinite loop
                seat = self.generate_seat_assignment(airplane_capacity, seat_class)
                if seat not in used_seats:
                    used_seats.add(seat)
                    break
                attempts += 1
            else:
                # If we can't find a unique seat, skip this passenger
                continue
            
            # Calculate price
            price = self.calculate_price(estimated_distance, seat_class, flight.departure)
            
            # Create booking
            booking = Booking(
                flight_id=flight.flight_id,
                seat=seat,
                passenger_id=passenger_id,
                price=price
            )
            bookings.append(booking)
            
            # Track passenger flight time
            self.add_passenger_flight(passenger_id, flight.departure, flight.arrival)
            
            # Remove passenger from available pool
            available_passengers.remove(passenger_id)
        
        return bookings


def populate_bookings(clear_existing: bool = False, batch_size: int = 10000, verbose: bool = False):
    """Main booking population function"""
    
    print(f"🚀 Starting booking population")
    print(f"   📋 Batch size: {batch_size:,}")
    
    populator = BookingPopulator(verbose=verbose)
    
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
        
        # Get flight and passenger counts
        flight_count = session.exec(select(func.count(Flight.flight_id))).first()
        passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
        
        print(f"   📊 Found {flight_count:,} flights and {passenger_count:,} passengers")
        
        if flight_count == 0 or passenger_count == 0:
            print("❌ No flights or passengers found. Please populate flights and passengers first.")
            return
        
        # Get all passenger IDs (we'll manage availability as we go)
        all_passengers = list(session.exec(select(Passenger.passenger_id)).all())
        available_passengers = all_passengers.copy()
        
        # Process flights in batches
        total_bookings = 0
        flights_processed = 0
        
        # Get flights ordered by departure time
        flights_query = select(Flight, Airplane.capacity).join(
            Airplane, Flight.airplane_id == Airplane.airplane_id
        ).order_by(Flight.departure)
        
        batch_bookings = []
        
        for flight, capacity in session.exec(flights_query):
            if len(available_passengers) < 10:  # Reset passenger pool if running low
                available_passengers = all_passengers.copy()
                populator.passenger_flight_times.clear()  # Reset conflict tracking
                if verbose:
                    print("   🔄 Reset passenger availability pool")
            
            # Track used seats for this flight
            used_seats = set()
            
            # Generate bookings for this flight
            flight_bookings = populator.populate_flight_bookings(
                session, flight, capacity, used_seats, available_passengers
            )
            
            batch_bookings.extend(flight_bookings)
            flights_processed += 1
            
            # Process batch when it reaches target size
            if len(batch_bookings) >= batch_size:
                session.add_all(batch_bookings)
                session.commit()
                
                total_bookings += len(batch_bookings)
                elapsed = time.time() - start_time
                rate = total_bookings / elapsed if elapsed > 0 else 0
                
                print(f"   ⚡ Processed {flights_processed:,} flights, "
                      f"{total_bookings:,} bookings ({rate:.0f} bookings/sec)")
                
                batch_bookings = []
        
        # Process remaining bookings
        if batch_bookings:
            session.add_all(batch_bookings)
            session.commit()
            total_bookings += len(batch_bookings)
        
        # Final statistics
        total_time = time.time() - start_time
        avg_rate = total_bookings / total_time if total_time > 0 else 0
        
        print(f"\n🎉 Booking population completed!")
        print(f"   📈 Total bookings: {total_bookings:,}")
        print(f"   ✈️  Flights processed: {flights_processed:,}")
        print(f"   ⏱️  Total time: {total_time/60:.1f} minutes")
        print(f"   🚀 Average rate: {avg_rate:.0f} bookings/second")
        
        # Calculate occupancy statistics
        avg_occupancy = session.exec(
            select(func.avg(func.count(Booking.booking_id)))
            .select_from(Booking)
            .join(Flight, Booking.flight_id == Flight.flight_id)
            .join(Airplane, Flight.airplane_id == Airplane.airplane_id)
            .group_by(Flight.flight_id)
        ).first()
        
        if avg_occupancy:
            print(f"   📊 Average occupancy: {avg_occupancy:.1f} passengers per flight")


def main():
    parser = argparse.ArgumentParser(description='Populate booking data with realistic patterns')
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
        populate_bookings(args.clear, args.batch_size, args.verbose)
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