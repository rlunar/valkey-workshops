#!/usr/bin/env python3
"""
Optimized Passenger Population Script for FlughafenDB

This script generates 10 million passenger records with:
- Unique passport numbers per country (format: {ISO_CODE}{sequential_number})
- Unique email addresses globally
- Realistic geographic distribution
- Sequential processing by country for efficiency
- Shared addresses within cities to reduce data generation overhead

Usage:
    python scripts/populate_passengers_v2.py [--total-records 10000000] [--clear]
"""

import random
import argparse
from datetime import date, timedelta
from typing import List, Tuple
from faker import Faker
from sqlmodel import Session, text, func
import sys
import os
import time

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.passenger import Passenger, PassengerDetails


class OptimizedPassengerGenerator:
    """Optimized passenger generator with proper uniqueness constraints"""
    
    def __init__(self):
        print("🔧 Initializing optimized passenger generator...")
        
        # Initialize Faker instances
        self.fakers = {
            'en_US': Faker('en_US'), 'en_GB': Faker('en_GB'), 'de_DE': Faker('de_DE'),
            'fr_FR': Faker('fr_FR'), 'es_ES': Faker('es_ES'), 'it_IT': Faker('it_IT'),
            'pt_BR': Faker('pt_BR'), 'ru_RU': Faker('ru_RU'), 'en_AU': Faker('en_AU'),
            'en_CA': Faker('en_CA'), 'nl_NL': Faker('nl_NL'), 'es_MX': Faker('es_MX'),
            'tr_TR': Faker('tr_TR'), 'pl_PL': Faker('pl_PL'), 'pt_PT': Faker('pt_PT'),
            'cs_CZ': Faker('cs_CZ'), 'sv_SE': Faker('sv_SE'), 'no_NO': Faker('no_NO'),
            'da_DK': Faker('da_DK'), 'fi_FI': Faker('fi_FI')
        }
        
        # Age distribution weights (18-80, peak at 25-45)
        self.age_weights = [1] * 8 + [3] * 10 + [5] * 15 + [3] * 10 + [2] * 10 + [1] * 10
        self.age_range = list(range(18, 81))
        
        # Country processing plan (country, percentage, iso_code, faker_locale, cities)
        self.country_plan = [
            ('United States', 22.0, 'US', 'en_US', [
                ('New York', 10001, 12.0), ('Los Angeles', 90001, 10.0), ('Chicago', 60601, 6.0),
                ('Houston', 77001, 5.5), ('San Francisco', 94101, 5.0), ('Miami', 33101, 4.5),
                ('Seattle', 98101, 4.0), ('Boston', 2101, 4.0), ('Washington', 20001, 4.0),
                ('Atlanta', 30301, 3.5), ('Dallas', 75201, 3.5), ('Philadelphia', 19101, 3.0)
            ]),
            ('China', 9.5, 'CN', 'en_US', [
                ('Shanghai', 200001, 20.0), ('Beijing', 100001, 18.0), ('Shenzhen', 518001, 15.0),
                ('Guangzhou', 510001, 12.0), ('Hangzhou', 310001, 8.0), ('Chengdu', 610001, 6.0)
            ]),
            ('United Kingdom', 8.2, 'GB', 'en_GB', [
                ('London', 10001, 50.0), ('Manchester', 10002, 12.0), ('Birmingham', 10003, 10.0),
                ('Edinburgh', 10004, 8.0), ('Glasgow', 10005, 6.0), ('Liverpool', 10006, 5.0)
            ]),
            ('Germany', 7.5, 'DE', 'de_DE', [
                ('Berlin', 10115, 18.0), ('Munich', 80331, 16.0), ('Frankfurt', 60311, 14.0),
                ('Hamburg', 20095, 12.0), ('Cologne', 50667, 10.0), ('Stuttgart', 70173, 8.0)
            ]),
            ('France', 6.8, 'FR', 'fr_FR', [
                ('Paris', 75001, 40.0), ('Lyon', 69001, 12.0), ('Marseille', 13001, 10.0),
                ('Nice', 6000, 8.0), ('Toulouse', 31000, 6.0), ('Strasbourg', 67000, 5.0)
            ]),
            ('Japan', 6.8, 'JP', 'en_US', [
                ('Tokyo', 1000001, 40.0), ('Osaka', 5300001, 20.0), ('Yokohama', 2200001, 10.0),
                ('Nagoya', 4600001, 8.0), ('Sapporo', 600001, 6.0), ('Fukuoka', 8100001, 5.0)
            ]),
            ('India', 5.5, 'IN', 'en_US', [
                ('Mumbai', 400001, 25.0), ('Delhi', 110001, 20.0), ('Bangalore', 560001, 15.0),
                ('Hyderabad', 500001, 10.0), ('Chennai', 600001, 8.0), ('Pune', 411001, 7.0)
            ]),
            ('Italy', 5.2, 'IT', 'it_IT', [
                ('Rome', 185, 25.0), ('Milan', 20121, 25.0), ('Naples', 80121, 12.0),
                ('Turin', 10121, 10.0), ('Florence', 50121, 8.0), ('Bologna', 40121, 6.0)
            ]),
            ('Spain', 4.8, 'ES', 'es_ES', [
                ('Madrid', 28001, 35.0), ('Barcelona', 8001, 30.0), ('Valencia', 46001, 10.0),
                ('Seville', 41001, 8.0), ('Bilbao', 48001, 5.0), ('Málaga', 29001, 4.0)
            ]),
            ('Canada', 4.5, 'CA', 'en_CA', [
                ('Toronto', 10001, 35.0), ('Vancouver', 10003, 25.0), ('Montreal', 10002, 20.0),
                ('Calgary', 10004, 10.0), ('Ottawa', 10005, 6.0), ('Edmonton', 10006, 4.0)
            ]),
            ('Brazil', 4.2, 'BR', 'pt_BR', [
                ('São Paulo', 1310, 30.0), ('Rio de Janeiro', 20040, 25.0), ('Brasília', 70040, 12.0),
                ('Salvador', 40070, 8.0), ('Belo Horizonte', 30112, 6.0), ('Fortaleza', 60175, 5.0)
            ]),
            ('South Korea', 4.2, 'KR', 'en_US', [
                ('Seoul', 100001, 55.0), ('Busan', 600001, 20.0), ('Incheon', 400001, 12.0),
                ('Daegu', 700001, 8.0), ('Daejeon', 300001, 5.0)
            ]),
            ('Australia', 3.8, 'AU', 'en_AU', [
                ('Sydney', 2000, 35.0), ('Melbourne', 3000, 30.0), ('Brisbane', 4000, 15.0),
                ('Perth', 6000, 10.0), ('Adelaide', 5000, 6.0), ('Canberra', 2600, 4.0)
            ]),
            ('Mexico', 3.8, 'MX', 'es_MX', [
                ('Mexico City', 1000, 40.0), ('Guadalajara', 44100, 15.0), ('Monterrey', 64000, 12.0),
                ('Cancún', 77500, 10.0), ('Tijuana', 22000, 8.0), ('Puebla', 72000, 7.0)
            ]),
            ('Saudi Arabia', 3.2, 'SA', 'en_US', [
                ('Riyadh', 11564, 40.0), ('Jeddah', 21577, 30.0), ('Dammam', 32253, 15.0),
                ('Mecca', 24231, 10.0), ('Medina', 42311, 5.0)
            ]),
            ('Netherlands', 3.2, 'NL', 'nl_NL', [
                ('Amsterdam', 1012, 45.0), ('Rotterdam', 3011, 20.0), ('The Hague', 2511, 15.0),
                ('Utrecht', 3511, 12.0), ('Eindhoven', 5611, 8.0)
            ]),
            ('Turkey', 2.8, 'TR', 'tr_TR', [
                ('Istanbul', 34000, 50.0), ('Ankara', 6000, 20.0), ('Izmir', 35000, 15.0),
                ('Antalya', 7000, 10.0), ('Bursa', 16000, 5.0)
            ]),
            ('Russia', 2.8, 'RU', 'ru_RU', [
                ('Moscow', 101000, 45.0), ('Saint Petersburg', 190000, 25.0), ('Novosibirsk', 630000, 8.0),
                ('Yekaterinburg', 620000, 6.0), ('Nizhny Novgorod', 603000, 5.0), ('Kazan', 420000, 4.0)
            ])
        ]
        
        # Global counters for uniqueness
        self.passport_counters = {}  # Per country
        self.email_counter = 0
        self.global_passenger_id = 0  # Track global passenger ID
        
        print(f"   ✅ Configured {len(self.country_plan)} countries")
    
    def generate_country_batch(self, country_name: str, iso_code: str, faker_locale: str, 
                              cities: List[Tuple], num_passengers: int, batch_size: int = 50000) -> List[str]:
        """Generate passengers for a specific country in batches"""
        
        print(f"\n🌍 Processing {country_name} ({num_passengers:,} passengers)")
        
        # Initialize passport counter for this country
        if iso_code not in self.passport_counters:
            self.passport_counters[iso_code] = 0
        
        faker = self.fakers[faker_locale]
        city_weights = [city[2] for city in cities]
        
        # Pre-generate addresses for each city (shared within city)
        city_addresses = {}
        for city_name, base_zip, _ in cities:
            # Generate 10-20 addresses per city that will be shared
            addresses = []
            for _ in range(random.randint(10, 20)):
                street = faker.street_address().replace("'", "''")
                max_variation = min(999, 99999 - base_zip)
                if max_variation > 0:
                    zip_code = base_zip + random.randint(0, max_variation)
                else:
                    zip_code = base_zip
                addresses.append((street, zip_code))
            city_addresses[city_name] = addresses
        
        sql_batches = []
        passengers_processed = 0
        
        while passengers_processed < num_passengers:
            current_batch_size = min(batch_size, num_passengers - passengers_processed)
            
            passenger_values = []
            detail_values = []
            
            for i in range(current_batch_size):
                # Generate unique passport
                self.passport_counters[iso_code] += 1
                passport = f"{iso_code}{self.passport_counters[iso_code]:07d}"
                
                # Generate unique names
                first_name = faker.first_name().replace("'", "''")
                last_name = faker.last_name().replace("'", "''")
                
                # Select city and address
                selected_city = random.choices(cities, weights=city_weights)[0]
                city_name, _, _ = selected_city
                street, zip_code = random.choice(city_addresses[city_name])
                
                # Generate other details
                age = random.choices(self.age_range, weights=self.age_weights)[0]
                # More variable birthdate calculation
                days_variation = random.randint(-180, 180)  # ±6 months variation
                birth_date = date.today() - timedelta(days=age * 365 + random.randint(0, 365) + days_variation)
                sex = random.choice(['M', 'F'])
                
                # Generate unique email (required for all passengers)
                self.email_counter += 1
                email = f"user{self.email_counter:08d}@example.com"
                
                # Generate phone (required for all passengers)
                phone = faker.phone_number().replace("'", "''")
                
                # Build SQL values
                passenger_values.append(f"('{passport}', '{first_name}', '{last_name}')")
                
                email_val = f"'{email}'"
                phone_val = f"'{phone}'"
                city_escaped = city_name.replace("'", "''")
                country_escaped = country_name.replace("'", "''")
                
                # Use global passenger ID
                self.global_passenger_id += 1
                detail_values.append(
                    f"({self.global_passenger_id}, '{birth_date}', '{sex}', '{street}', "
                    f"'{city_escaped}', {zip_code}, '{country_escaped}', {email_val}, {phone_val})"
                )
            
            # Build SQL statements
            passenger_sql = f"INSERT INTO passenger (passportno, firstname, lastname) VALUES {','.join(passenger_values)}"
            detail_sql = f"""INSERT INTO passengerdetails 
                (passenger_id, birthdate, sex, street, city, zip, country, emailaddress, telephoneno) VALUES 
                {','.join(detail_values)}"""
            
            sql_batches.append((passenger_sql, detail_sql))
            passengers_processed += current_batch_size
            
            print(f"   📦 Generated batch: {passengers_processed:,}/{num_passengers:,} passengers")
        
        return sql_batches


def populate_passengers_optimized(total_records: int = 10_000_000, clear_existing: bool = False):
    """Optimized passenger population with sequential country processing"""
    
    print(f"🚀 Starting OPTIMIZED passenger population:")
    print(f"   🎯 Target: {total_records:,} records")
    print(f"   📋 Strategy: Sequential country processing")
    
    # Initialize
    db_manager = DatabaseManager()
    generator = OptimizedPassengerGenerator()
    
    # Ensure tables exist
    db_manager.create_tables()
    
    # Clear existing data if requested
    if clear_existing:
        print("   🗑️  Clearing existing data...")
        with Session(db_manager.engine) as session:
            session.execute(text('DELETE FROM passengerdetails'))
            session.execute(text('DELETE FROM passenger'))
            session.execute(text('ALTER TABLE passenger AUTO_INCREMENT = 1'))
            session.commit()
        print("   ✅ Database cleared")
    
    start_time = time.time()
    total_inserted = 0
    
    try:
        with db_manager.engine.connect() as connection:
            # Optimize for bulk operations
            if 'mysql' in str(connection.engine.url):
                connection.execute(text("SET autocommit=0"))
                connection.execute(text("SET foreign_key_checks=0"))
                connection.execute(text("SET unique_checks=0"))
            
            # Process each country sequentially
            for country_name, percentage, iso_code, faker_locale, cities in generator.country_plan:
                country_passengers = int(total_records * percentage / 100)
                
                if country_passengers == 0:
                    continue
                
                # Generate batches for this country
                sql_batches = generator.generate_country_batch(
                    country_name, iso_code, faker_locale, cities, country_passengers
                )
                
                # Execute batches
                for batch_num, (passenger_sql, detail_sql) in enumerate(sql_batches, 1):
                    batch_start = time.time()
                    
                    # Execute passenger insert
                    connection.execute(text(passenger_sql))
                    
                    # Execute details insert
                    connection.execute(text(detail_sql))
                    
                    # Commit batch
                    connection.commit()
                    
                    batch_time = time.time() - batch_start
                    batch_size = passenger_sql.count('(') - 1  # Count records in batch
                    rate = batch_size / batch_time if batch_time > 0 else 0
                    
                    total_inserted += batch_size
                    progress = (total_inserted / total_records) * 100
                    
                    print(f"   ⚡ Batch {batch_num}: {batch_size:,} records in {batch_time:.1f}s "
                          f"({rate:,.0f} rec/sec) - Progress: {progress:.1f}%")
            
            # Re-enable checks
            if 'mysql' in str(connection.engine.url):
                connection.execute(text("SET foreign_key_checks=1"))
                connection.execute(text("SET unique_checks=1"))
                connection.execute(text("SET autocommit=1"))
    
    except Exception as e:
        print(f"❌ Error during population: {e}")
        raise
    
    total_time = time.time() - start_time
    avg_rate = total_inserted / total_time if total_time > 0 else 0
    
    print(f"\n🎉 Population completed successfully!")
    print(f"   📈 Total records: {total_inserted:,}")
    print(f"   ⏱️  Total time: {total_time/60:.1f} minutes")
    print(f"   🚀 Average rate: {avg_rate:,.0f} records/second")
    print(f"   💾 Database size: ~{total_inserted * 200 / 1024 / 1024:.0f} MB")


def main():
    parser = argparse.ArgumentParser(description='Optimized passenger population with proper uniqueness')
    parser.add_argument('--total-records', type=int, default=10_000_000,
                       help='Total number of records to generate (default: 10,000,000)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing passenger data before starting')
    
    args = parser.parse_args()
    
    if args.total_records <= 0:
        print("❌ Error: total-records must be positive")
        return 1
    
    try:
        populate_passengers_optimized(args.total_records, args.clear)
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())