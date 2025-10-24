#!/usr/bin/env python3
"""
Test runner for database-related tests.

This script runs all database tests and provides a summary of results.
It's designed to be used during development and CI/CD processes.
"""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all database tests and return results."""
    backend_dir = Path(__file__).parent.parent
    
    test_files = [
        "tests/test_database_models.py",
        "tests/test_database_config.py", 
        "tests/test_database_integration.py"
    ]
    
    print("Running Database Tests for Airport Workshop System")
    print("=" * 60)
    
    all_passed = True
    results = {}
    
    for test_file in test_files:
        print(f"\n🧪 Running {test_file}...")
        
        try:
            result = subprocess.run(
                ["uv", "run", "pytest", test_file, "-v", "--tb=short"],
                cwd=backend_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"✅ {test_file} - All tests passed")
                results[test_file] = "PASSED"
            else:
                print(f"❌ {test_file} - Some tests failed")
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                print("STDERR:", result.stderr[-500:])  # Last 500 chars
                results[test_file] = "FAILED"
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file} - Tests timed out")
            results[test_file] = "TIMEOUT"
            all_passed = False
        except Exception as e:
            print(f"💥 {test_file} - Error running tests: {e}")
            results[test_file] = "ERROR"
            all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_file, status in results.items():
        status_icon = {
            "PASSED": "✅",
            "FAILED": "❌", 
            "TIMEOUT": "⏰",
            "ERROR": "💥"
        }.get(status, "❓")
        
        print(f"{status_icon} {test_file}: {status}")
    
    if all_passed:
        print("\n🎉 All database tests passed!")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Check the output above for details.")
        return 1


def run_quick_validation():
    """Run a quick validation of the database setup."""
    print("\n🔍 Quick Database Setup Validation")
    print("-" * 40)
    
    try:
        # Test imports
        from airport.database.models import Airport, Airline, Flight, Passenger, Booking
        from airport.database.config import DatabaseConfig, initialize_database
        print("✅ All imports successful")
        
        # Test basic configuration
        config = DatabaseConfig()
        assert config.db_type == 'sqlite'
        print("✅ Database configuration created")
        
        # Test initialization
        config.initialize()
        print("✅ Database initialized")
        
        # Test table creation
        config.create_tables()
        print("✅ Tables created")
        
        # Test basic model creation
        with config.get_session_context() as session:
            airport = Airport(iata="VAL", icao="KVAL", name="Validation Airport")
            session.add(airport)
        print("✅ Basic model operations work")
        
        config.close()
        print("✅ Database connection closed")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


if __name__ == "__main__":
    print("Database Test Suite for Valkey Airport Workshop")
    print("=" * 60)
    
    # Run quick validation first
    if not run_quick_validation():
        print("\n💥 Quick validation failed. Skipping full test suite.")
        sys.exit(1)
    
    # Run full test suite
    exit_code = run_tests()
    sys.exit(exit_code)