#!/usr/bin/env python3
"""
Example script showing how to use Country data with Airport data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import Session, select
    from models.database import DatabaseManager
    from models import Airport, AirportGeo, Country
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def show_country_airport_examples():
    """Show examples of using Country data with Airport data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("🌍 Country and Airport Data Examples")
        print("=" * 37)
        
        with Session(db_manager.engine) as session:
            # Check if we have data
            country_count = len(session.exec(select(Country)).all())
            airport_count = len(session.exec(select(Airport)).all())
            
            print(f"Database contains:")
            print(f"- {country_count:,} countries")
            print(f"- {airport_count:,} airports")
            
            if country_count == 0:
                print("\n⚠ No country data found. Run: python scripts/download_countries.py")
                return False
            
            if airport_count == 0:
                print("\n⚠ No airport data found. Run: python scripts/download_airports.py")
                return False
            
            print("\n" + "=" * 50)
            
            # Example 1: Find countries with airports
            print("\n1. Countries with airports in our database:")
            
            # Get countries that have airports (using the normalized relationship)
            countries_with_airports = session.exec(
                select(Country)
                .join(AirportGeo, Country.country_id == AirportGeo.country_id)
                .distinct()
                .order_by(Country.name)
            ).all()
            
            print(f"Found {len(countries_with_airports)} countries with airports")
            
            # Show sample countries and their airport counts
            print("\nSample countries with airport counts:")
            for country in countries_with_airports[:10]:
                airport_count = session.exec(
                    select(Airport)
                    .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
                    .where(AirportGeo.country_id == country.country_id)
                ).all()
                
                iso_code = f"({country.iso_code})" if country.iso_code else "(no ISO)"
                print(f"  {country.name} {iso_code}: {len(airport_count)} airports")
            
            # Example 2: Show countries with ISO codes but no airports
            print(f"\n2. Countries with ISO codes but no airports in our database:")
            
            countries_without_airports = []
            all_countries = session.exec(select(Country).where(Country.iso_code.is_not(None))).all()
            
            for country in all_countries:
                # Check if this country has any airports (using normalized relationship)
                has_airports = session.exec(
                    select(AirportGeo)
                    .where(AirportGeo.country_id == country.country_id)
                ).first()
                
                if not has_airports:
                    countries_without_airports.append(country)
            
            print(f"Found {len(countries_without_airports)} countries with ISO codes but no airports")
            print("Sample countries without airports:")
            for country in countries_without_airports[:10]:
                print(f"  {country.name} ({country.iso_code})")
            
            # Example 3: Major airports with country information
            print(f"\n3. Major international airports with country details:")
            
            major_iata_codes = ["JFK", "LAX", "LHR", "CDG", "NRT", "SIN", "DXB", "FRA", "AMS", "HKG"]
            
            for iata in major_iata_codes:
                airport_query = (
                    select(Airport, AirportGeo, Country)
                    .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
                    .outerjoin(Country, AirportGeo.country_id == Country.country_id)
                    .where(Airport.iata == iata)
                )
                
                result = session.exec(airport_query).first()
                if result:
                    airport, geo, country_record = result
                    
                    country_name = country_record.name if country_record else "Unknown"
                    iso_info = f" (ISO: {country_record.iso_code})" if country_record and country_record.iso_code else ""
                    dafif_info = f" (DAFIF: {country_record.dafif_code})" if country_record and country_record.dafif_code else ""
                    
                    print(f"  {airport.iata}/{airport.icao}: {airport.name}")
                    print(f"    Location: {geo.city}, {country_name}{iso_info}{dafif_info}")
            
            # Example 4: Country code lookup functionality
            print(f"\n4. Country code lookup examples:")
            
            # Show how to look up country codes for airport countries
            sample_countries = ["United States", "Germany", "Japan", "Australia", "United Kingdom"]
            
            for country_name in sample_countries:
                country_record = session.exec(
                    select(Country)
                    .where(Country.name == country_name)
                ).first()
                
                if country_record:
                    airport_count = len(session.exec(
                        select(Airport)
                        .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
                        .where(AirportGeo.country_id == country_record.country_id)
                    ).all())
                    
                    codes = []
                    if country_record.iso_code:
                        codes.append(f"ISO: {country_record.iso_code}")
                    if country_record.dafif_code:
                        codes.append(f"DAFIF: {country_record.dafif_code}")
                    
                    code_info = f" ({', '.join(codes)})" if codes else " (no codes)"
                    print(f"  {country_name}{code_info} - {airport_count} airports")
                else:
                    print(f"  {country_name} - not found in country database")
            
            print(f"\n✅ Country and airport data examples completed!")
            return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = show_country_airport_examples()
    sys.exit(0 if success else 1)