#!/usr/bin/env python3
"""
Test Flight Population

Quick test to validate flight generation logic before full population.
"""

import os
import sys
from datetime import datetime, timedelta
from sqlmodel import Session, select, func

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.database import DatabaseManager
    from models.flight import Flight
    from models.route import Route
    from models.airport import Airport
    from models.airline import Airline
    from scripts.flight_config import FlightConfig
    from scripts.populate_flights_comprehensive import ComprehensiveFlightPopulator
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False


def test_configuration():
    """Test flight configuration"""
    print("Testing Flight Configuration")
    print("-" * 30)
    
    config = FlightConfig()
    
    # Test airport tier classification
    test_cases = [915, 558, 200, 50, 10, 1]
    
    for route_count in test_cases:
        tier = config.get_airport_tier(route_count)
        print(f"Routes: {route_count:3d} -> {tier['name']} "
              f"(Daily flights: {tier['daily_flights_range'][0]}-{tier['daily_flights_range'][1]})")
    
    # Test seasonal multipliers
    print(f"\nSeasonal multipliers:")
    for month in [1, 4, 7, 10]:
        mult = config.get_seasonal_multiplier(month)
        season_name = ['Winter', 'Spring', 'Summer', 'Fall'][month//4]
        print(f"  Month {month:2d} ({season_name}): {mult}x")
    
    print("✅ Configuration test passed")


def test_database_connectivity():
    """Test database connectivity and data availability"""
    print("\nTesting Database Connectivity")
    print("-" * 35)
    
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Dependencies not available")
        return False
    
    try:
        db_manager = DatabaseManager()
        
        with Session(db_manager.engine) as session:
            # Check data availability
            route_count = session.exec(select(func.count(Route.route_id))).first()
            airport_count = session.exec(select(func.count(Airport.airport_id))).first()
            airline_count = session.exec(select(func.count(Airline.airline_id))).first()
            
            print(f"Routes: {route_count:,}")
            print(f"Airports: {airport_count:,}")
            print(f"Airlines: {airline_count:,}")
            
            if route_count == 0:
                print("❌ No routes found - import route data first")
                return False
            
            if airport_count == 0:
                print("❌ No airports found - import airport data first")
                return False
            
            if airline_count == 0:
                print("❌ No airlines found - import airline data first")
                return False
            
            print("✅ Database connectivity test passed")
            return True
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_flight_generation():
    """Test flight generation for a small sample"""
    print("\nTesting Flight Generation (Sample)")
    print("-" * 40)
    
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Dependencies not available")
        return False
    
    try:
        db_manager = DatabaseManager()
        populator = ComprehensiveFlightPopulator(db_manager)
        
        # Test for just one week
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        
        print(f"Test period: {start_date.date()} to {end_date.date()}")
        
        # Clear any existing test flights
        cleared = populator.clear_flights_in_range(start_date, end_date)
        print(f"Cleared {cleared} existing flights in test range")
        
        # Generate flights for test period with limited routes
        created = populator.populate_flights(start_date, end_date, max_routes=50)
        
        if created > 0:
            print(f"✅ Generated {created:,} test flights successfully")
            
            # Show sample flights
            with Session(db_manager.engine) as session:
                sample_query = (
                    select(Flight.flightno, Flight.departure, Flight.arrival)
                    .where(
                        Flight.departure >= start_date,
                        Flight.departure <= end_date
                    )
                    .limit(10)
                )
                
                print("\nSample flights generated:")
                for flight in session.exec(sample_query).all():
                    print(f"  {flight.flightno}: {flight.departure} -> {flight.arrival}")
            
            return True
        else:
            print("❌ No flights generated")
            return False
            
    except Exception as e:
        print(f"❌ Flight generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return 1
    
    load_dotenv()
    
    print("Flight Population Test Suite")
    print("=" * 35)
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Configuration
    try:
        test_configuration()
        tests_passed += 1
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
    
    # Test 2: Database connectivity
    try:
        if test_database_connectivity():
            tests_passed += 1
    except Exception as e:
        print(f"❌ Database test failed: {e}")
    
    # Test 3: Flight generation (only if database test passed)
    if tests_passed >= 2:
        try:
            if test_flight_generation():
                tests_passed += 1
        except Exception as e:
            print(f"❌ Flight generation test failed: {e}")
    else:
        print("\nSkipping flight generation test due to previous failures")
    
    # Summary
    print(f"\nTest Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Ready for full flight population.")
        print("\nTo populate flights for 2 years, run:")
        print("  python scripts/populate_flights_comprehensive.py")
    else:
        print("❌ Some tests failed. Please fix issues before running full population.")
    
    return 0 if tests_passed == total_tests else 1


if __name__ == "__main__":
    exit(main())