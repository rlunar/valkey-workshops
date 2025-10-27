#!/usr/bin/env python3
"""
Test Reduced Flight Generation

Quick test to validate the new flight generation produces ~890K flights for 100M bookings.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from models.database import DatabaseManager
    from scripts.populate_flights_comprehensive import ComprehensiveFlightPopulator
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False

def test_flight_generation():
    """Test flight generation with reduced parameters"""
    
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Dependencies not available")
        return
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return
    
    load_dotenv()
    
    print("🧪 Testing Reduced Flight Generation")
    print("=" * 40)
    
    # Initialize
    db_manager = DatabaseManager()
    populator = ComprehensiveFlightPopulator(db_manager, verbose=True, flight_reduction_factor=0.2)
    
    # Test with a small date range (1 week)
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 1, 7)
    
    print(f"Test period: {start_date.date()} to {end_date.date()}")
    print(f"Flight reduction factor: 20% (80% reduction)")
    
    try:
        # Generate flights for test period
        flights_created = populator.populate_flights(
            start_date=start_date,
            end_date=end_date,
            max_routes=100  # Small sample for testing
        )
        
        print(f"\n✅ Test completed!")
        print(f"   Flights created (1 week): {flights_created:,}")
        
        # Extrapolate to full year
        days_tested = 7
        days_per_year = 365
        estimated_yearly = flights_created * (days_per_year / days_tested)
        
        print(f"   Estimated yearly flights: {estimated_yearly:,.0f}")
        
        # Calculate estimated bookings
        avg_load_factor = 0.75
        avg_capacity = 150
        estimated_bookings = estimated_yearly * avg_load_factor * avg_capacity
        
        print(f"   Estimated yearly bookings: {estimated_bookings:,.0f}")
        
        # Compare to target
        target_bookings = 100_000_000
        if 80_000_000 <= estimated_bookings <= 120_000_000:
            print(f"   🎯 Within target range for 100M bookings!")
        else:
            adjustment = target_bookings / estimated_bookings
            print(f"   ⚠️  Adjustment needed: {adjustment:.2f}x")
            print(f"   💡 Suggested flight reduction factor: {0.2 * adjustment:.2f}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_flight_generation()