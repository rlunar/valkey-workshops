#!/usr/bin/env python3
"""
Quick test to verify SQL case syntax works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from sqlmodel import Session, select, func
    from sqlalchemy import case
    from models.database import DatabaseManager
    from models.airline import Airline
    from models.airplane import Airplane
    from dotenv import load_dotenv
    
    load_dotenv()
    
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Test the case statement syntax
        test_query = (
            select(
                Airline.name,
                func.sum(case((Airplane.capacity >= 250, 1), else_=0)).label('wide_body'),
                func.sum(case(((Airplane.capacity >= 120) & (Airplane.capacity < 250), 1), else_=0)).label('narrow_body'),
                func.sum(case(((Airplane.capacity >= 50) & (Airplane.capacity < 120), 1), else_=0)).label('regional'),
                func.sum(case((Airplane.capacity < 50, 1), else_=0)).label('small')
            )
            .join(Airplane, Airline.airline_id == Airplane.airline_id)
            .group_by(Airline.airline_id, Airline.name)
            .having(func.count(Airplane.airplane_id) >= 5)
            .order_by(func.count(Airplane.airplane_id).desc())
            .limit(5)
        )
        
        print("Testing SQL case syntax...")
        results = session.exec(test_query).all()
        
        print("✅ SQL syntax test passed!")
        print(f"Found {len(results)} airlines with 5+ aircraft")
        
        if results:
            print("\nTop airlines by fleet composition:")
            print(f"{'Airline':<25} {'Wide':<5} {'Narrow':<7} {'Regional':<8} {'Small':<5}")
            print("-" * 50)
            for airline_name, wide, narrow, regional, small in results:
                print(f"{airline_name[:24]:<25} {wide:<5} {narrow:<7} {regional:<8} {small:<5}")
        
except Exception as e:
    print(f"❌ SQL syntax error: {e}")
    sys.exit(1)

print("🎉 All tests passed!")