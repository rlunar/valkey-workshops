#!/usr/bin/env python3
"""
Database setup script for Flughafen DB
Creates tables and optionally loads sample data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.database import DatabaseManager
    from models import *  # Import all models
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def setup_database():
    """Create database tables"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        # Create all tables
        print("Creating database tables...")
        db_manager.create_tables()
        print("✓ Database tables created successfully!")
        
        return True
        
    except Exception as e:
        print(f"Database setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file configuration")
        print("2. Ensure your database server is running")
        print("3. Verify database credentials and permissions")
        return False

def check_database_config():
    """Check database configuration"""
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return False
    
    load_dotenv()
    
    db_type = os.getenv("DB_TYPE", "mysql")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME", "flughafendb")
    user = os.getenv("DB_USER")
    
    print(f"Database Configuration:")
    print(f"  Type: {db_type}")
    print(f"  Host: {host}")
    print(f"  Port: {port or 'default'}")
    print(f"  Database: {name}")
    print(f"  User: {user}")
    
    if not user or user == "username":
        print("⚠ Please update your database credentials in .env")
        return False
    
    return True

if __name__ == "__main__":
    print("Flughafen DB Setup")
    print("=" * 20)
    
    if not check_database_config():
        sys.exit(1)
    
    if setup_database():
        print("\n✓ Database setup completed successfully!")
        print("You can now run: uv run python scripts/database_example.py")
    else:
        sys.exit(1)