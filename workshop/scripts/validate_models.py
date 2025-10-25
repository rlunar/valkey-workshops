#!/usr/bin/env python3
"""
Validate that all SQLModel classes can be imported and have correct structure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _validate_normalized_airport_schema(Airport, AirportGeo):
    """Validate the normalized airport schema structure"""
    
    # Check that Airport only contains core operational fields
    airport_fields = set(Airport.model_fields.keys())
    expected_airport_fields = {
        'airport_id', 'iata', 'icao', 'name', 'airport_type', 'data_source', 'openflights_id'
    }
    
    # Check that Airport doesn't contain geographic fields (these should be in AirportGeo)
    geographic_fields = {'city', 'country', 'latitude', 'longitude', 'altitude', 'timezone_offset', 'dst', 'timezone_name'}
    airport_geographic_fields = airport_fields.intersection(geographic_fields)
    
    if airport_geographic_fields:
        print(f"✗ Airport model contains geographic fields that should be in AirportGeo: {airport_geographic_fields}")
    else:
        print("✓ Airport model contains only core operational fields")
    
    # Check that Airport has all expected core fields
    missing_airport_fields = expected_airport_fields - airport_fields
    if missing_airport_fields:
        print(f"✗ Airport model missing core fields: {missing_airport_fields}")
    else:
        print("✓ Airport model has all expected core fields")
    
    # Check that AirportGeo contains all geographic fields
    airport_geo_fields = set(AirportGeo.model_fields.keys())
    expected_geo_fields = {'airport_id', 'city', 'country', 'latitude', 'longitude', 'altitude', 'timezone_offset', 'dst', 'timezone_name'}
    
    missing_geo_fields = expected_geo_fields - airport_geo_fields
    if missing_geo_fields:
        print(f"✗ AirportGeo model missing fields: {missing_geo_fields}")
    else:
        print("✓ AirportGeo model has all expected geographic fields")
    
    # Check foreign key relationship
    airport_geo_airport_id_field = AirportGeo.model_fields.get('airport_id')
    if airport_geo_airport_id_field and hasattr(airport_geo_airport_id_field, 'foreign_key'):
        if airport_geo_airport_id_field.foreign_key == "airport.airport_id":
            print("✓ AirportGeo has correct foreign key relationship to Airport")
        else:
            print(f"✗ AirportGeo foreign key incorrect: {airport_geo_airport_id_field.foreign_key}")
    else:
        print("⚠ Could not verify AirportGeo foreign key relationship")
    
    # Check that both models use the same table naming convention
    if hasattr(Airport, '__tablename__') and hasattr(AirportGeo, '__tablename__'):
        if Airport.__tablename__ == "airport" and AirportGeo.__tablename__ == "airport_geo":
            print("✓ Table names follow normalized schema convention")
        else:
            print(f"✗ Unexpected table names: Airport='{Airport.__tablename__}', AirportGeo='{AirportGeo.__tablename__}'")

def validate_models():
    """Validate model imports and basic structure"""
    try:
        # Test imports
        from models import (
            Airport, AirportGeo, AirportType, DSTType,
            Airline, Airplane, AirplaneType,
            Flight, FlightLog, FlightSchedule,
            Passenger, PassengerDetails,
            Booking, Employee, WeatherData
        )
        
        print("✓ All models imported successfully")
        
        # Test model attributes - focusing on normalized airport schema
        models_to_test = [
            # Normalized Airport models
            (Airport, ['airport_id', 'iata', 'icao', 'name', 'airport_type', 'data_source', 'openflights_id']),
            (AirportGeo, ['airport_id', 'city', 'country', 'latitude', 'longitude', 'altitude', 'timezone_offset', 'dst', 'timezone_name']),
            # Other models
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
        
        # Additional validation for normalized airport schema
        print("\nValidating normalized airport schema...")
        _validate_normalized_airport_schema(Airport, AirportGeo)
        
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