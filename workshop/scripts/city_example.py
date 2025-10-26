#!/usr/bin/env python3
"""
City Model Usage Example

Demonstrates how to use the new City model and CityAirportRelation
for flight planning and population-based route analysis.
"""

import os
import sys
from sqlmodel import Session, select, func

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.city import City, CityAirportRelation
from models.airport import Airport
from models.country import Country


def demonstrate_city_queries():
    """Demonstrate various city-related queries for flight planning"""
    
    print("City Model Usage Examples")
    print("=" * 30)
    
    # Initialize database
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        
        # 1. Get top 10 cities by population
        print("\n1. Top 10 Cities by Population:")
        print("-" * 35)
        
        top_cities = session.exec(
            select(City.name, City.population, City.flight_demand_score, City.recommended_daily_flights)
            .where(City.population.is_not(None))
            .order_by(City.population.desc())
            .limit(10)
        ).all()
        
        for city in top_cities:
            print(f"{city.name:25} | Pop: {city.population:>10,} | Demand: {city.flight_demand_score:>5.2f} | Flights/day: {city.recommended_daily_flights:>3}")
        
        # 2. Cities with their primary airports
        print("\n2. Cities with Primary Airports:")
        print("-" * 40)
        
        cities_with_airports = session.exec(
            select(
                City.name.label('city_name'),
                City.population,
                Airport.name.label('airport_name'),
                Airport.iata,
                CityAirportRelation.distance_km
            )
            .join(CityAirportRelation, City.city_id == CityAirportRelation.city_id)
            .join(Airport, CityAirportRelation.airport_id == Airport.airport_id)
            .where(
                CityAirportRelation.is_primary_airport == True,
                City.population >= 1000000
            )
            .order_by(City.population.desc())
            .limit(10)
        ).all()
        
        for result in cities_with_airports:
            distance = f"{result.distance_km:.1f}km" if result.distance_km else "N/A"
            print(f"{result.city_name:20} | {result.airport_name:30} | {result.iata or 'N/A':>4} | {distance:>8}")
        
        # 3. Flight demand by country
        print("\n3. Flight Demand Summary by Country:")
        print("-" * 45)
        
        country_demand = session.exec(
            select(
                Country.name.label('country_name'),
                func.count(City.city_id).label('city_count'),
                func.sum(City.population).label('total_population'),
                func.sum(City.recommended_daily_flights).label('total_flights')
            )
            .join(City, Country.country_id == City.country_id)
            .where(City.population.is_not(None))
            .group_by(Country.country_id, Country.name)
            .order_by(func.sum(City.population).desc())
            .limit(10)
        ).all()
        
        for result in country_demand:
            print(f"{result.country_name:20} | Cities: {result.city_count:>3} | Pop: {result.total_population:>12,} | Flights/day: {result.total_flights:>5}")
        
        # 4. Underserved cities (high population, few airports)
        print("\n4. Potentially Underserved Cities:")
        print("-" * 40)
        
        # Subquery to count airports per city
        airport_count_subquery = (
            select(
                CityAirportRelation.city_id,
                func.count(CityAirportRelation.airport_id).label('airport_count')
            )
            .group_by(CityAirportRelation.city_id)
            .subquery()
        )
        
        underserved = session.exec(
            select(
                City.name,
                City.population,
                City.flight_demand_score,
                func.coalesce(airport_count_subquery.c.airport_count, 0).label('airport_count')
            )
            .join(airport_count_subquery, City.city_id == airport_count_subquery.c.city_id, isouter=True)
            .where(
                City.population >= 500000,
                func.coalesce(airport_count_subquery.c.airport_count, 0) <= 1
            )
            .order_by(City.population.desc())
            .limit(10)
        ).all()
        
        for city in underserved:
            print(f"{city.name:25} | Pop: {city.population:>10,} | Airports: {city.airport_count:>2} | Demand: {city.flight_demand_score:>5.2f}")
        
        # 5. Route recommendations between major cities
        print("\n5. Sample Route Recommendations:")
        print("-" * 40)
        
        # Get top cities with airports for route planning
        major_cities = session.exec(
            select(
                City.name.label('city_name'),
                City.population,
                City.flight_demand_score,
                Airport.iata,
                Country.name.label('country_name')
            )
            .join(CityAirportRelation, City.city_id == CityAirportRelation.city_id)
            .join(Airport, CityAirportRelation.airport_id == Airport.airport_id)
            .join(Country, City.country_id == Country.country_id, isouter=True)
            .where(
                CityAirportRelation.is_primary_airport == True,
                City.population >= 2000000,
                Airport.iata.is_not(None)
            )
            .order_by(City.population.desc())
            .limit(8)
        ).all()
        
        # Generate sample route recommendations
        routes = []
        for i, origin in enumerate(major_cities):
            for destination in major_cities[i+1:]:
                if origin.country_name != destination.country_name:  # International routes only
                    combined_demand = (float(origin.flight_demand_score) + float(destination.flight_demand_score)) / 2
                    routes.append({
                        'origin': f"{origin.city_name} ({origin.iata})",
                        'destination': f"{destination.city_name} ({destination.iata})",
                        'priority': combined_demand
                    })
        
        # Sort by priority and show top routes
        routes.sort(key=lambda x: x['priority'], reverse=True)
        for route in routes[:8]:
            print(f"{route['origin']:20} → {route['destination']:20} | Priority: {route['priority']:>5.2f}")


def demonstrate_city_statistics():
    """Show basic statistics about the city data"""
    
    print("\n\nCity Database Statistics")
    print("=" * 25)
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        
        # Total cities
        total_cities = session.exec(select(func.count(City.city_id))).first()
        print(f"Total cities in database: {total_cities:,}")
        
        # Cities with population data
        cities_with_pop = session.exec(
            select(func.count(City.city_id)).where(City.population.is_not(None))
        ).first()
        print(f"Cities with population data: {cities_with_pop:,}")
        
        # Total population covered
        total_population = session.exec(
            select(func.sum(City.population)).where(City.population.is_not(None))
        ).first()
        if total_population:
            print(f"Total population covered: {total_population:,}")
        
        # Cities with airports
        cities_with_airports = session.exec(
            select(func.count(func.distinct(CityAirportRelation.city_id)))
        ).first()
        print(f"Cities with airport connections: {cities_with_airports:,}")
        
        # Average recommended flights per day
        avg_flights = session.exec(
            select(func.avg(City.recommended_daily_flights))
            .where(City.recommended_daily_flights.is_not(None))
        ).first()
        if avg_flights:
            print(f"Average recommended flights per day: {avg_flights:.1f}")
        
        # Population ranges
        print("\nPopulation Distribution:")
        ranges = [
            ("Mega cities (>5M)", 5000000),
            ("Major cities (1M-5M)", 1000000),
            ("Large cities (500K-1M)", 500000),
            ("Medium cities (100K-500K)", 100000),
            ("Small cities (50K-100K)", 50000),
        ]
        
        for label, min_pop in ranges:
            if label == "Major cities (1M-5M)":
                count = session.exec(
                    select(func.count(City.city_id))
                    .where(City.population >= min_pop, City.population < 5000000)
                ).first()
            elif label == "Large cities (500K-1M)":
                count = session.exec(
                    select(func.count(City.city_id))
                    .where(City.population >= min_pop, City.population < 1000000)
                ).first()
            elif label == "Medium cities (100K-500K)":
                count = session.exec(
                    select(func.count(City.city_id))
                    .where(City.population >= min_pop, City.population < 500000)
                ).first()
            elif label == "Small cities (50K-100K)":
                count = session.exec(
                    select(func.count(City.city_id))
                    .where(City.population >= min_pop, City.population < 100000)
                ).first()
            else:  # Mega cities
                count = session.exec(
                    select(func.count(City.city_id))
                    .where(City.population >= min_pop)
                ).first()
            
            print(f"  {label:25}: {count:>6,}")


def main():
    """Main function to run city model examples"""
    try:
        demonstrate_city_queries()
        demonstrate_city_statistics()
        
        print("\n" + "=" * 50)
        print("City model demonstration completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python scripts/download_cities.py' to populate city data")
        print("2. Run 'python scripts/cities_flight_analysis.py' for detailed analysis")
        print("3. Use the city data for flight route planning and frequency optimization")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure to:")
        print("1. Set up your database connection in .env")
        print("2. Run the city data download script first")
        print("3. Ensure all required dependencies are installed")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())