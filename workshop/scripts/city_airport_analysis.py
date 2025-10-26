#!/usr/bin/env python3
"""
Analyze city-airport relationships using the updated AirportGeo model
with country and ISO_a2 information.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, func
from models.database import DatabaseManager
from models.city import City, CityAirportRelation
from models.airport import Airport
from models.airport_geo import AirportGeo
from models.country import Country


def analyze_city_airport_relationships():
    """Analyze city-airport relationships with geographic and country data"""
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        print("🌍 City-Airport Relationship Analysis")
        print("=" * 50)
        
        # Get total counts
        total_cities = session.exec(select(func.count(City.city_id))).first()
        total_airports = session.exec(select(func.count(Airport.airport_id))).first()
        total_relations = session.exec(select(func.count(CityAirportRelation.relation_id))).first()
        
        print(f"📊 Database Overview:")
        print(f"  • Cities: {total_cities:,}")
        print(f"  • Airports: {total_airports:,}")
        print(f"  • City-Airport Relations: {total_relations:,}")
        print()
        
        # Analyze relationships by country using updated AirportGeo model
        print("🗺️  Top Countries by City-Airport Connections:")
        country_analysis = session.exec(
            select(
                AirportGeo.country,
                AirportGeo.iso_a2,
                func.count(CityAirportRelation.relation_id).label('connections')
            ).select_from(
                CityAirportRelation.__table__.join(
                    AirportGeo.__table__, 
                    CityAirportRelation.airport_id == AirportGeo.airport_id
                )
            ).where(
                AirportGeo.country.is_not(None),
                AirportGeo.iso_a2.is_not(None)
            ).group_by(
                AirportGeo.country, AirportGeo.iso_a2
            ).order_by(
                func.count(CityAirportRelation.relation_id).desc()
            ).limit(10)
        ).all()
        
        for country, iso_a2, connections in country_analysis:
            print(f"  {iso_a2:2} | {country:<25} | {connections:,} connections")
        print()
        
        # Find cities with the most airport connections
        print("🏙️  Cities with Most Airport Connections:")
        city_connections = session.exec(
            select(
                City.name,
                City.country_code,
                City.population,
                func.count(CityAirportRelation.relation_id).label('airport_count')
            ).select_from(
                City.__table__.join(
                    CityAirportRelation.__table__,
                    City.city_id == CityAirportRelation.city_id
                )
            ).group_by(
                City.city_id, City.name, City.country_code, City.population
            ).order_by(
                func.count(CityAirportRelation.relation_id).desc()
            ).limit(10)
        ).all()
        
        for city_name, country_code, population, airport_count in city_connections:
            pop_str = f"{population:,}" if population else "Unknown"
            print(f"  {city_name:<20} ({country_code}) | Pop: {pop_str:>10} | {airport_count} airports")
        print()
        
        # Analyze primary airport relationships
        print("✈️  Primary Airport Analysis:")
        primary_airports = session.exec(
            select(func.count(CityAirportRelation.relation_id)).where(
                CityAirportRelation.is_primary_airport == True
            )
        ).first()
        
        secondary_airports = session.exec(
            select(func.count(CityAirportRelation.relation_id)).where(
                CityAirportRelation.is_primary_airport == False
            )
        ).first()
        
        print(f"  • Primary airport relationships: {primary_airports:,}")
        print(f"  • Secondary airport relationships: {secondary_airports:,}")
        print()
        
        # Show example relationships with full geographic data
        print("🔍 Sample City-Airport Relationships with Geographic Data:")
        sample_relations = session.exec(
            select(
                City.name.label('city_name'),
                City.country_code.label('city_country'),
                Airport.name.label('airport_name'),
                Airport.iata,
                AirportGeo.country.label('airport_country'),
                AirportGeo.iso_a2,
                CityAirportRelation.distance_km,
                CityAirportRelation.is_primary_airport,
                CityAirportRelation.accessibility_score
            ).select_from(
                CityAirportRelation.__table__.join(
                    City.__table__, CityAirportRelation.city_id == City.city_id
                ).join(
                    Airport.__table__, CityAirportRelation.airport_id == Airport.airport_id
                ).join(
                    AirportGeo.__table__, Airport.airport_id == AirportGeo.airport_id
                )
            ).where(
                CityAirportRelation.is_primary_airport == True,
                AirportGeo.country.is_not(None)
            ).order_by(CityAirportRelation.distance_km).limit(5)
        ).all()
        
        for relation in sample_relations:
            city_name, city_country, airport_name, iata, airport_country, iso_a2, distance, is_primary, accessibility = relation
            primary_str = "PRIMARY" if is_primary else "Secondary"
            print(f"  {city_name} ({city_country}) ↔ {airport_name} ({iata}) [{iso_a2}]")
            print(f"    Distance: {distance}km | {primary_str} | Accessibility: {accessibility}/10")
            print()


if __name__ == "__main__":
    try:
        analyze_city_airport_relationships()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)