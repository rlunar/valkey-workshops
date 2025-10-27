#!/usr/bin/env python3
"""
Flight Count Calculation for 100M Bookings

Working backwards from target bookings to determine optimal flight count.
"""

def calculate_optimal_flights():
    """Calculate optimal flight count for 100M bookings"""
    
    # Target metrics
    target_bookings = 100_000_000  # 100M bookings
    total_passengers = 10_000_000  # 10M passengers
    
    # Realistic assumptions
    avg_load_factor = 0.75  # 75% average load factor
    avg_aircraft_capacity = 150  # Average capacity across all aircraft types
    
    # Calculate passengers per flight
    avg_passengers_per_flight = avg_aircraft_capacity * avg_load_factor
    print(f"Average passengers per flight: {avg_passengers_per_flight:.1f}")
    
    # Calculate required flights for 100M bookings
    required_flights = target_bookings / avg_passengers_per_flight
    print(f"Required flights for 100M bookings: {required_flights:,.0f}")
    
    # Calculate average bookings per passenger
    avg_bookings_per_passenger = target_bookings / total_passengers
    print(f"Average bookings per passenger: {avg_bookings_per_passenger:.1f}")
    
    # Alternative calculation: if each passenger books multiple flights
    # More realistic: passengers book 2-4 flights per year on average
    realistic_bookings_per_passenger = 3.0
    realistic_total_bookings = total_passengers * realistic_bookings_per_passenger
    realistic_required_flights = realistic_total_bookings / avg_passengers_per_flight
    
    print(f"\nMore realistic scenario:")
    print(f"Bookings per passenger: {realistic_bookings_per_passenger}")
    print(f"Total bookings: {realistic_total_bookings:,.0f}")
    print(f"Required flights: {realistic_required_flights:,.0f}")
    
    # Current vs recommended
    current_flights = 4_600_000
    current_bookings = current_flights * avg_passengers_per_flight
    
    print(f"\nCurrent situation:")
    print(f"Current flights: {current_flights:,}")
    print(f"Current potential bookings: {current_bookings:,.0f}")
    print(f"Reduction needed: {(current_flights - required_flights) / current_flights * 100:.1f}%")
    
    return int(required_flights)

if __name__ == "__main__":
    optimal_flights = calculate_optimal_flights()
    print(f"\nRecommendation: Generate ~{optimal_flights:,} flights")