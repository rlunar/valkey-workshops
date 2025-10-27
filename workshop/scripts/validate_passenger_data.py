#!/usr/bin/env python3
"""
Validate passenger data quality and distribution after population
"""

import sys
import os
from collections import Counter
from sqlmodel import Session, select, func

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.passenger import Passenger, PassengerDetails


def validate_data_integrity():
    """Check basic data integrity"""
    db_manager = DatabaseManager()
    
    print("🔍 Validating Data Integrity...")
    print("-" * 50)
    
    with Session(db_manager.engine) as session:
        # Count records
        passenger_count = session.exec(select(func.count(Passenger.passenger_id))).first()
        details_count = session.exec(select(func.count(PassengerDetails.passenger_id))).first()
        
        print(f"Passenger records: {passenger_count:,}")
        print(f"Passenger details: {details_count:,}")
        
        # Check for mismatches
        if passenger_count != details_count:
            print(f"❌ Record count mismatch: {abs(passenger_count - details_count)} difference")
            return False
        else:
            print("✅ Record counts match")
        
        # Check for duplicate passport numbers
        duplicate_passports = session.exec(
            select(func.count(Passenger.passportno))
            .group_by(Passenger.passportno)
            .having(func.count(Passenger.passportno) > 1)
        ).all()
        
        if duplicate_passports:
            print(f"❌ Found {len(duplicate_passports)} duplicate passport numbers")
            return False
        else:
            print("✅ All passport numbers are unique")
        
        # Check for missing required fields
        missing_names = session.exec(
            select(func.count(Passenger.passenger_id))
            .where((Passenger.firstname == '') | (Passenger.lastname == ''))
        ).first()
        
        if missing_names > 0:
            print(f"❌ Found {missing_names} records with missing names")
            return False
        else:
            print("✅ All records have names")
        
        # Check for invalid birth dates
        from datetime import date
        invalid_dates = session.exec(
            select(func.count(PassengerDetails.passenger_id))
            .where((PassengerDetails.birthdate > date.today()) | 
                   (PassengerDetails.birthdate < date(1920, 1, 1)))
        ).first()
        
        if invalid_dates > 0:
            print(f"❌ Found {invalid_dates} records with invalid birth dates")
            return False
        else:
            print("✅ All birth dates are valid")
    
    return True


def analyze_geographic_distribution():
    """Analyze geographic distribution of passengers"""
    db_manager = DatabaseManager()
    
    print("\n🌍 Geographic Distribution Analysis...")
    print("-" * 50)
    
    with Session(db_manager.engine) as session:
        # Country distribution
        country_stats = session.exec(
            select(PassengerDetails.country, func.count(PassengerDetails.passenger_id))
            .group_by(PassengerDetails.country)
            .order_by(func.count(PassengerDetails.passenger_id).desc())
        ).all()
        
        total_records = sum(count for _, count in country_stats)
        
        print(f"Top 15 Countries by Passenger Count:")
        print(f"{'Country':<20} {'Count':<12} {'Percentage':<10}")
        print("-" * 45)
        
        for i, (country, count) in enumerate(country_stats[:15]):
            percentage = (count / total_records) * 100
            print(f"{country:<20} {count:<12,} {percentage:<10.2f}%")
        
        # City distribution for top countries
        print(f"\nTop Cities in Major Countries:")
        for country, _ in country_stats[:5]:
            city_stats = session.exec(
                select(PassengerDetails.city, func.count(PassengerDetails.passenger_id))
                .where(PassengerDetails.country == country)
                .group_by(PassengerDetails.city)
                .order_by(func.count(PassengerDetails.passenger_id).desc())
                .limit(5)
            ).all()
            
            print(f"\n{country}:")
            for city, count in city_stats:
                print(f"  {city}: {count:,}")


def analyze_demographic_distribution():
    """Analyze demographic distribution"""
    db_manager = DatabaseManager()
    
    print("\n👥 Demographic Distribution Analysis...")
    print("-" * 50)
    
    with Session(db_manager.engine) as session:
        # Gender distribution
        gender_stats = session.exec(
            select(PassengerDetails.sex, func.count(PassengerDetails.passenger_id))
            .group_by(PassengerDetails.sex)
        ).all()
        
        total_records = sum(count for _, count in gender_stats)
        
        print("Gender Distribution:")
        for gender, count in gender_stats:
            percentage = (count / total_records) * 100
            gender_label = "Male" if gender == "M" else "Female" if gender == "F" else "Unknown"
            print(f"  {gender_label}: {count:,} ({percentage:.1f}%)")
        
        # Age distribution
        from datetime import date
        current_year = date.today().year
        
        # Use a simpler approach that's compatible with ONLY_FULL_GROUP_BY
        age_stats = session.exec(
            select(
                (func.floor((current_year - func.extract('year', PassengerDetails.birthdate)) / 10) * 10).label('age_group'),
                func.count(PassengerDetails.passenger_id).label('count')
            )
            .group_by(func.floor((current_year - func.extract('year', PassengerDetails.birthdate)) / 10) * 10)
            .order_by(func.floor((current_year - func.extract('year', PassengerDetails.birthdate)) / 10) * 10)
        ).all()
        
        print("\nAge Distribution (by decade):")
        for age_group, count in age_stats:
            percentage = (count / total_records) * 100
            print(f"  {int(age_group)}-{int(age_group)+9}: {count:,} ({percentage:.1f}%)")
        
        # Contact information coverage
        email_count = session.exec(
            select(func.count(PassengerDetails.passenger_id))
            .where(PassengerDetails.emailaddress.is_not(None))
        ).first()
        
        phone_count = session.exec(
            select(func.count(PassengerDetails.passenger_id))
            .where(PassengerDetails.telephoneno.is_not(None))
        ).first()
        
        email_percentage = (email_count / total_records) * 100
        phone_percentage = (phone_count / total_records) * 100
        
        print(f"\nContact Information Coverage:")
        print(f"  Email addresses: {email_count:,} ({email_percentage:.1f}%)")
        print(f"  Phone numbers: {phone_count:,} ({phone_percentage:.1f}%)")


def main():
    """Run all validation checks"""
    print("🚀 Passenger Data Validation Report")
    print("=" * 60)
    
    # Data integrity checks
    integrity_ok = validate_data_integrity()
    
    if not integrity_ok:
        print("\n❌ Data integrity issues found. Please review and fix before proceeding.")
        return 1
    
    # Distribution analyses
    analyze_geographic_distribution()
    analyze_demographic_distribution()
    
    print("\n" + "=" * 60)
    print("✅ Validation completed successfully!")
    
    return 0


if __name__ == "__main__":
    exit(main())