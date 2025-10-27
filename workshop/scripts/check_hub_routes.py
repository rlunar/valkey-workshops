#!/usr/bin/env python3
"""
Check major hub airport route counts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import DatabaseManager
from models.route import Route
from sqlmodel import Session, select, func
from dotenv import load_dotenv

load_dotenv()
db_manager = DatabaseManager()

with Session(db_manager.engine) as session:
    # Check what major hub airports we have in routes
    major_hubs = ['ATL', 'FRA', 'MEX', 'JFK', 'MCO', 'LAS', 'LHR', 'CDG', 'LAX', 'DFW', 'ORD', 'AMS']
    
    print('Major Hub Airport Route Counts:')
    print('=' * 40)
    
    hub_data = []
    for hub in major_hubs:
        # Count routes from this hub
        outbound = session.exec(
            select(func.count(Route.route_id))
            .where(Route.source_airport_code == hub)
        ).first() or 0
        
        # Count routes to this hub  
        inbound = session.exec(
            select(func.count(Route.route_id))
            .where(Route.destination_airport_code == hub)
        ).first() or 0
        
        total = outbound + inbound
        hub_data.append((hub, total, outbound, inbound))
    
    # Sort by total routes descending
    hub_data.sort(key=lambda x: x[1], reverse=True)
    
    for hub, total, outbound, inbound in hub_data:
        if total > 0:
            print(f'{hub}: {total} routes ({outbound} outbound, {inbound} inbound)')
        else:
            print(f'{hub}: No routes found')
    
    print('\nTop 20 airports by route count:')
    print('=' * 35)
    
    # Get top airports by route count
    top_airports_query = """
    SELECT airport_code, route_count FROM (
        SELECT source_airport_code as airport_code, COUNT(*) as route_count
        FROM route 
        WHERE source_airport_code IS NOT NULL
        GROUP BY source_airport_code
        UNION ALL
        SELECT destination_airport_code as airport_code, COUNT(*) as route_count  
        FROM route
        WHERE destination_airport_code IS NOT NULL
        GROUP BY destination_airport_code
    ) combined
    GROUP BY airport_code
    ORDER BY SUM(route_count) DESC
    LIMIT 20
    """
    
    result = session.exec(select(func.text(top_airports_query)))
    for row in result:
        print(f'{row[0]}: {row[1]} routes')