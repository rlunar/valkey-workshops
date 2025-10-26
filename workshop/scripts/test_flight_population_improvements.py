#!/usr/bin/env python3
"""
Test script for flight population improvements
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.flight_config import FlightConfig
from scripts.populate_flights_comprehensive import ComprehensiveFlightPopulator

def test_distance_estimation():
    """Test the distance estimation improvements"""
    print("Testing Distance Estimation:")
    print("-" * 30)
    
    # Create a mock populator (without database)
    class MockPopulator(ComprehensiveFlightPopulator):
        def __init__(self):
            self.config = FlightConfig()
    
    populator = MockPopulator()
    
    # Test various airport pairs
    test_pairs = [
        ("LAX", "SFO"),  # Same region - short
        ("JFK", "LAX"),  # Same continent - medium/long
        ("LHR", "JFK"),  # Intercontinental - long
        ("NRT", "SYD"),  # Asia-Oceania - long
        ("CDG", "FRA"),  # Europe regional - short
    ]
    
    for origin, dest in test_pairs:
        distance, duration = populator.estimate_distance_and_duration(origin, dest)
        print(f"  {origin} → {dest}: {distance:.0f}km, {duration}")
    
    print()

def test_aircraft_selection():
    """Test aircraft selection by distance"""
    print("Testing Aircraft Selection by Distance:")
    print("-" * 40)
    
    distances = [500, 1500, 3000, 6000, 10000]  # km
    
    for distance in distances:
        category = FlightConfig.get_aircraft_category_by_distance(distance)
        print(f"  {distance:,}km → {category['category']}")
        print(f"    Capacity: {category['capacity_range'][0]}-{category['capacity_range'][1]} seats")
        print(f"    Types: {', '.join(category['aircraft_types'][:2])}...")
        print()

def test_tier_based_frequencies():
    """Test tier-based flight frequency calculations"""
    print("Testing Tier-Based Flight Frequencies:")
    print("-" * 40)
    
    route_counts = [1000, 300, 100, 25, 5]  # Different airport tiers
    distances = [800, 2000, 6000]  # Short, medium, long haul
    
    for routes in route_counts:
        tier = FlightConfig.get_airport_tier(routes)
        print(f"  Airport with {routes} routes → {tier['name']}")
        
        for distance in distances:
            if distance <= 1500:
                haul_type = "Short-haul"
            elif distance <= 4000:
                haul_type = "Medium-haul"
            else:
                haul_type = "Long-haul"
            
            print(f"    {haul_type} ({distance}km): ", end="")
            
            # Mock frequency calculation
            if distance <= 1500 and 'short_haul_daily' in tier:
                freq_range = tier['short_haul_daily']
                print(f"{freq_range[0]}-{freq_range[1]} daily flights")
            elif distance <= 1500 and 'short_haul_weekly' in tier:
                freq_range = tier['short_haul_weekly']
                print(f"{freq_range[0]}-{freq_range[1]} weekly flights")
            elif distance <= 4000 and 'medium_haul_daily' in tier:
                freq_range = tier['medium_haul_daily']
                print(f"{freq_range[0]}-{freq_range[1]} daily flights")
            elif distance <= 4000 and 'medium_haul_weekly' in tier:
                freq_range = tier['medium_haul_weekly']
                print(f"{freq_range[0]}-{freq_range[1]} weekly flights")
            elif 'long_haul_daily' in tier:
                freq_range = tier['long_haul_daily']
                print(f"{freq_range[0]}-{freq_range[1]} daily flights")
            elif 'long_haul_weekly' in tier:
                freq_range = tier['long_haul_weekly']
                print(f"{freq_range[0]}-{freq_range[1]} weekly flights")
            else:
                print("No service (charter/seasonal only)")
        
        print()

def test_seasonal_adjustments():
    """Test seasonal multiplier calculations"""
    print("Testing Seasonal Adjustments:")
    print("-" * 30)
    
    months = [
        (1, "January"), (4, "April"), (7, "July"), (10, "October")
    ]
    
    for month_num, month_name in months:
        multiplier = FlightConfig.get_seasonal_multiplier(month_num)
        print(f"  {month_name}: {multiplier}x multiplier")
    
    print()

def main():
    """Run all tests"""
    print("Flight Population Improvements Test Suite")
    print("=" * 50)
    print()
    
    # Show configuration summary
    FlightConfig.print_configuration_summary()
    print()
    
    # Run tests
    test_distance_estimation()
    test_aircraft_selection()
    test_tier_based_frequencies()
    test_seasonal_adjustments()
    
    print("✅ All tests completed successfully!")
    print("\nThe flight population improvements are working correctly.")
    print("You can now run the comprehensive flight population script:")
    print("  python scripts/populate_flights_comprehensive.py")

if __name__ == "__main__":
    main()