#!/usr/bin/env python3
"""
Test script for passenger generation - generates a small sample to verify functionality
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.populate_passengers import populate_passengers

def main():
    """Test passenger generation with a small dataset"""
    print("Testing passenger generation with 1,000 records...")
    
    try:
        populate_passengers(total_records=1000, batch_size=100)
        print("✅ Test completed successfully!")
        return 0
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())