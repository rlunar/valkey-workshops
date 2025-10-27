#!/usr/bin/env python3
"""
Test script for booking population - validates the approach with a small dataset
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.booking import Booking
from models.flight import Flight
from models.passenger import Passenger
from models.airplane import Airplane
from sqlmodel import Session, select, func


def test_booking_logic():
    """Test the booking population logic with a small sample"""
    
    print("🧪 Testing booking population logic...")
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Get sample data
        sample_flights = session.exec(select(Flight).limit(5)).all()
        sample_passengers = session.exec(select(Passenger.passenger_id).limit(100)).all()
        
        if not sample_flights or not sample_passengers:
            print("❌ No sample data found. Please populate flights and passengers first.")
            return
        
        print(f"   📊 Found {len(sample_flights)} sample flights")
        print(f"   👥 Found {len(sample_passengers)} sample passengers")
        
        # Test peak time detection
        from scripts.populate_bookings import BookingPopulator
        populator = BookingPopulator(verbose=True)
        
        for flight in sample_flights:
            is_peak = populator.is_peak_time(flight.departure)
            occupancy = populator.calculate_occupancy_rate(flight.departure, 150)
            
            print(f"   ✈️  Flight {flight.flightno}: {flight.departure}")
            print(f"      Peak time: {is_peak}, Target occupancy: {occupancy:.1%}")
        
        # Test seat assignment
        for capacity in [50, 150, 300]:
            seat = populator.generate_seat_assignment(capacity, 'economy')
            print(f"   💺 Capacity {capacity}: Sample seat {seat}")
        
        # Test pricing
        base_distance = 1000  # km
        for seat_class in ['economy', 'business', 'first']:
            price = populator.calculate_price(base_distance, seat_class, datetime.now())
            print(f"   💰 {seat_class.title()} class price: ${price}")
        
        print("✅ Booking logic test completed successfully!")


if __name__ == "__main__":
    test_booking_logic()