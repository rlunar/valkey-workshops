#!/usr/bin/env python3
"""Check route distribution in database"""

import sys
sys.path.append('.')
from models.database import DatabaseManager
from models.route import Route
from sqlmodel import Session, select, func

def main():
    db_manager = DatabaseManager()
    with Session(db_manager.engine) as session:
        # Check if JFK routes exist
        jfk_routes = session.exec(
            select(func.count(Route.route_id))
            .where((Route.source_airport_code == 'JFK') | (Route.destination_airport_code == 'JFK'))
        ).first()
        print(f'JFK routes in database: {jfk_routes}')
        
        # Check top airports by route count
        outbound_counts = session.exec(
            select(Route.source_airport_code, func.count(Route.route_id))
            .where(Route.source_airport_code.is_not(None))
            .group_by(Route.source_airport_code)
            .order_by(func.count(Route.route_id).desc())
            .limit(15)
        ).all()
        
        print('\nTop 15 airports by outbound routes:')
        for airport, count in outbound_counts:
            print(f'{airport}: {count} routes')
        
        # Check major hubs specifically
        major_hubs = ['ATL', 'ORD', 'LHR', 'CDG', 'FRA', 'LAX', 'DFW', 'JFK', 'AMS']
        print('\nMajor hub route counts:')
        for hub in major_hubs:
            hub_routes = session.exec(
                select(func.count(Route.route_id))
                .where((Route.source_airport_code == hub) | (Route.destination_airport_code == hub))
            ).first()
            print(f'{hub}: {hub_routes} total routes')

if __name__ == "__main__":
    main()