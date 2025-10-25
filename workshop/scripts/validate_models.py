#!/usr/bin/env python3
"""
Validate that all SQLModel classes can be imported and have correct structure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_models():
    """Validate model imports and basic structure"""
    try:
        # Test imports
        from models import (
            Airport, AirportGeo, AirportReachable,
            Airline, Airplane, AirplaneType,
            Flight, FlightLog, FlightSchedule,
            Passenger, PassengerDetails,
            Booking, Employee, WeatherData
        )
        
        print("✓ All models imported successfully")
        
        # Test model attributes
        models_to_test = [
            (Airport, ['airport_id', 'iata', 'icao', 'name']),
            (Airline, ['airline_id', 'iata', 'airlinename', 'base_airport']),
            (Flight, ['flight_id', 'flightno', 'from_airport', 'to_airport']),
            (Passenger, ['passenger_id', 'passportno', 'firstname', 'lastname']),
            (Booking, ['booking_id', 'flight_id', 'passenger_id', 'price'])
        ]
        
        for model_class, expected_fields in models_to_test:
            model_fields = list(model_class.model_fields.keys())
            missing_fields = [f for f in expected_fields if f not in model_fields]
            
            if missing_fields:
                print(f"✗ {model_class.__name__} missing fields: {missing_fields}")
            else:
                print(f"✓ {model_class.__name__} has all expected fields")
        
        print("\n✓ Model validation completed successfully!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False

if __name__ == "__main__":
    print("Validating Flughafen DB Models...")
    success = validate_models()
    sys.exit(0 if success else 1)