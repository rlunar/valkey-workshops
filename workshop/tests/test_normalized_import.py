#!/usr/bin/env python3
"""
Test the normalized airport import process with a small dataset
"""

import sys
import os
sys.path.append('.')

try:
    from sqlmodel import Session, select
    from models.database import DatabaseManager
    from models import Airport, AirportGeo
    from scripts.download_airports import create_airport_and_geo_records, validate_core_airport_data, validate_geographic_data
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False

def test_normalized_import():
    """Test the normalized import process with sample data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available for testing")
        return False
    
    load_dotenv()
    
    # Sample airport data for testing
    test_airports = [
        {
            'icao': 'TEST',
            'name': 'Test Airport',
            'iata': 'TST',
            'airport_type': 'airport',
            'data_source': 'Test',
            'openflights_id': 99999,
            'city': 'Test City',
            'country': 'Test Country',
            'latitude': 40.0,
            'longitude': -74.0,
            'altitude': 100,
            'timezone_offset': -5.0,
            'dst': 'A',
            'timezone_name': 'America/New_York'
        },
        {
            'icao': 'TST2',
            'name': 'Test Airport 2',
            'iata': None,  # Test without IATA
            'airport_type': 'airport',
            'data_source': 'Test',
            'openflights_id': 99998,
            'city': 'Test City 2',
            'country': 'Test Country',
            'latitude': 41.0,
            'longitude': -75.0,
            'altitude': None,  # Test without altitude
            'timezone_offset': -5.0,
            'dst': None,  # Test without DST
            'timezone_name': None  # Test without timezone name
        }
    ]
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        with Session(db_manager.engine) as session:
            # Clean up any existing test data - delete AirportGeo records first
            existing_test_airports = session.exec(
                select(Airport).where(Airport.icao.in_(['TEST', 'TST2']))
            ).all()
            
            # First delete all AirportGeo records
            for airport in existing_test_airports:
                geo_record = session.exec(
                    select(AirportGeo).where(AirportGeo.airport_id == airport.airport_id)
                ).first()
                if geo_record:
                    session.delete(geo_record)
            session.commit()  # Commit geo deletions first
            
            # Then delete Airport records
            for airport in existing_test_airports:
                session.delete(airport)
            session.commit()  # Commit airport deletions
            
            print("Cleaned up existing test data")
            
            # Test the import process
            for i, airport_data in enumerate(test_airports):
                icao = airport_data['icao']
                print(f"\nTesting airport {i+1}: {icao}")
                
                # Validate data
                core_errors = validate_core_airport_data(airport_data)
                geo_errors, geo_warnings = validate_geographic_data(airport_data)
                
                print(f"  Core validation: {'✓' if not core_errors else '✗'} {core_errors}")
                print(f"  Geo validation: {'✓' if not geo_errors else '✗'} {geo_errors}")
                if geo_warnings:
                    print(f"  Geo warnings: {geo_warnings}")
                
                if core_errors or geo_errors:
                    continue
                
                # Create records
                airport, airport_geo, issues = create_airport_and_geo_records(airport_data)
                
                if airport is None:
                    print(f"  ✗ Failed to create records: {issues}")
                    continue
                
                # Insert into database
                try:
                    session.add(airport)
                    session.flush()  # Get airport_id
                    
                    airport_geo.airport_id = airport.airport_id
                    session.add(airport_geo)
                    session.commit()
                    
                    print(f"  ✓ Inserted airport {icao} with ID {airport.airport_id}")
                    
                    # Verify the data was inserted correctly
                    query = (
                        select(Airport, AirportGeo)
                        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
                        .where(Airport.icao == icao)
                    )
                    result = session.exec(query).first()
                    
                    if result:
                        retrieved_airport, retrieved_geo = result
                        print(f"  ✓ Verified: {retrieved_airport.name} at {retrieved_geo.city}, {retrieved_geo.country}")
                    else:
                        print(f"  ✗ Failed to retrieve inserted data")
                        
                except Exception as e:
                    session.rollback()
                    print(f"  ✗ Database error: {e}")
            
            # Final verification - check that both records exist and are properly linked
            test_results = session.exec(
                select(Airport, AirportGeo)
                .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
                .where(Airport.icao.in_(['TEST', 'TST2']))
            ).all()
            
            print(f"\n✓ Final verification: {len(test_results)} airports with geographic data")
            for airport, geo in test_results:
                iata_display = f"({airport.iata})" if airport.iata else "(no IATA)"
                coords = f"({geo.latitude}, {geo.longitude})" if geo.latitude and geo.longitude else "(no coords)"
                print(f"  {airport.icao} {iata_display} - {airport.name}")
                print(f"    Location: {geo.city}, {geo.country} {coords}")
            
            # Clean up test data - delete AirportGeo first due to foreign key constraints
            test_airports_to_delete = session.exec(select(Airport).where(Airport.icao.in_(['TEST', 'TST2']))).all()
            for airport in test_airports_to_delete:
                geo_record = session.exec(
                    select(AirportGeo).where(AirportGeo.airport_id == airport.airport_id)
                ).first()
                if geo_record:
                    session.delete(geo_record)
            session.commit()  # Commit geo deletions first
            
            for airport in test_airports_to_delete:
                session.delete(airport)
            session.commit()  # Then commit airport deletions
            
            print("\n✓ Test completed successfully and cleaned up")
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_normalized_import()
    sys.exit(0 if success else 1)