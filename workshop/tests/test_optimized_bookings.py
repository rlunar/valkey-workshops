#!/usr/bin/env python3
"""
Quick test for the optimized booking population
Tests with a small number of flights to validate the approach
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.populate_bookings_optimized import populate_bookings_optimized


def test_optimized_bookings():
    """Test optimized booking population with a small dataset"""
    
    print("🧪 Testing optimized booking population...")
    print("   This will process only 100 flights as a test")
    
    try:
        # Test with 100 flights, clear existing data
        populate_bookings_optimized(
            clear_existing=True,
            max_flights=100,
            batch_size=1000,
            verbose=True
        )
        
        print("\n✅ Optimized booking test completed successfully!")
        print("   If this works well, you can run the full population with:")
        print("   python scripts/populate_bookings_optimized.py --clear")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_optimized_bookings()