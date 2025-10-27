#!/usr/bin/env python3
"""
Passenger Population Script for FlughafenDB

High-performance script that generates 10 million passenger records with:
- Realistic geographic distributions based on travel patterns
- Country-specific passport formats using ISO alpha-2 codes
- Locale-appropriate names and addresses
- Optimized bulk database operations

Performance optimizations:
- Bulk inserts using executemany()
- Reduced database round trips
- Efficient memory management
- Progress tracking

Usage:
    python scripts/populate_passengers.py [--batch-size 50000] [--total-records 10000000]
"""

import random
import string
import argparse
from datetime import date, datetime, timedelta
from typing import List, Tuple, Dict, Set
from faker import Faker
from sqlmodel import Session, select, text, func
import sys
import os
import time

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.passenger import Passenger, PassengerDetails


class PassengerGenerator:
    """Optimized passenger data generator with proper uniqueness and sequential processing"""
    
    def __init__(self):
        print("🔧 Initializing optimized data generator...")
        
        # Initialize Faker instances for different locales
        self.fakers = {
            'en_US': Faker('en_US'), 'en_GB': Faker('en_GB'), 'de_DE': Faker('de_DE'),
            'fr_FR': Faker('fr_FR'), 'es_ES': Faker('es_ES'), 'it_IT': Faker('it_IT'),
            'pt_BR': Faker('pt_BR'), 'ru_RU': Faker('ru_RU'), 'en_AU': Faker('en_AU'),
            'en_CA': Faker('en_CA'), 'nl_NL': Faker('nl_NL'), 'es_MX': Faker('es_MX'),
            'tr_TR': Faker('tr_TR'), 'pl_PL': Faker('pl_PL'), 'pt_PT': Faker('pt_PT'),
            'cs_CZ': Faker('cs_CZ'), 'sv_SE': Faker('sv_SE'), 'no_NO': Faker('no_NO'),
            'da_DK': Faker('da_DK'), 'fi_FI': Faker('fi_FI')
        }
        
        # Age distribution weights
        self.age_weights = [1] * 8 + [3] * 10 + [5] * 15 + [3] * 10 + [2] * 10 + [1] * 10
        self.age_range = list(range(18, 81))
        
        # Country-specific passport counters for uniqueness
        self.passport_counters = {}
        
        # Track used emails globally for uniqueness
        self.used_emails = set()
        self.email_counter = 0
        
        # Sequential country processing plan for 10M passengers
        # Each country gets processed completely before moving to the next
        self.country_plan = [
            # North America - Highest travel volume
            'United States': {
                'weight': 22.0, 'faker': 'en_US', 'iso_code': 'US',
                'cities': [
                    ('New York', 10001, 12.0), ('Los Angeles', 90001, 10.0), ('Chicago', 60601, 6.0),
                    ('Houston', 77001, 5.5), ('San Francisco', 94101, 5.0), ('Miami', 33101, 4.5),
                    ('Seattle', 98101, 4.0), ('Boston', 2101, 4.0), ('Washington', 20001, 4.0),
                    ('Atlanta', 30301, 3.5), ('Dallas', 75201, 3.5), ('Philadelphia', 19101, 3.0),
                    ('Phoenix', 85001, 2.5), ('Denver', 80201, 2.5), ('Las Vegas', 89101, 2.0),
                    ('San Diego', 92101, 2.0), ('Austin', 78701, 1.8), ('Charlotte', 28201, 1.5),
                    ('Portland', 97201, 1.2), ('Nashville', 37201, 1.0)
                ]
            },
            'Canada': {
                'weight': 4.5, 'faker': 'en_CA', 'iso_code': 'CA',
                'cities': [
                    ('Toronto', 10001, 35.0), ('Vancouver', 10003, 25.0), ('Montreal', 10002, 20.0),
                    ('Calgary', 10004, 10.0), ('Ottawa', 10005, 6.0), ('Edmonton', 10006, 4.0)
                ]
            },
            'Mexico': {
                'weight': 3.8, 'faker': 'es_MX', 'iso_code': 'MX',
                'cities': [
                    ('Mexico City', 1000, 40.0), ('Guadalajara', 44100, 15.0), ('Monterrey', 64000, 12.0),
                    ('Cancún', 77500, 10.0), ('Tijuana', 22000, 8.0), ('Puebla', 72000, 7.0),
                    ('León', 37000, 5.0), ('Mérida', 97000, 3.0)
                ]
            },
            
            # Europe - Major travel markets
            'United Kingdom': {
                'weight': 8.2, 'faker': 'en_GB', 'iso_code': 'GB',
                'cities': [
                    ('London', 10001, 50.0), ('Manchester', 10002, 12.0), ('Birmingham', 10003, 10.0),
                    ('Edinburgh', 10004, 8.0), ('Glasgow', 10005, 6.0), ('Liverpool', 10006, 5.0),
                    ('Leeds', 10007, 4.0), ('Bristol', 10008, 3.0), ('Newcastle', 10009, 2.0)
                ]
            },
            'Germany': {
                'weight': 7.5, 'faker': 'de_DE', 'iso_code': 'DE',
                'cities': [
                    ('Berlin', 10115, 18.0), ('Munich', 80331, 16.0), ('Frankfurt', 60311, 14.0),
                    ('Hamburg', 20095, 12.0), ('Cologne', 50667, 10.0), ('Stuttgart', 70173, 8.0),
                    ('Düsseldorf', 40210, 7.0), ('Dortmund', 44135, 5.0), ('Essen', 45127, 4.0),
                    ('Leipzig', 4109, 3.0), ('Bremen', 28195, 3.0)
                ]
            },
            'France': {
                'weight': 6.8, 'faker': 'fr_FR', 'iso_code': 'FR',
                'cities': [
                    ('Paris', 75001, 40.0), ('Lyon', 69001, 12.0), ('Marseille', 13001, 10.0),
                    ('Nice', 6000, 8.0), ('Toulouse', 31000, 6.0), ('Strasbourg', 67000, 5.0),
                    ('Nantes', 44000, 4.0), ('Bordeaux', 33000, 4.0), ('Lille', 59000, 3.0),
                    ('Montpellier', 34000, 3.0), ('Cannes', 6400, 2.5), ('Nancy', 54000, 2.5)
                ]
            },
            'Italy': {
                'weight': 5.2, 'faker': 'it_IT', 'iso_code': 'IT',
                'cities': [
                    ('Rome', 185, 25.0), ('Milan', 20121, 25.0), ('Naples', 80121, 12.0),
                    ('Turin', 10121, 10.0), ('Florence', 50121, 8.0), ('Bologna', 40121, 6.0),
                    ('Venice', 30121, 5.0), ('Genoa', 16121, 4.0), ('Palermo', 90121, 3.0), ('Bari', 70121, 2.0)
                ]
            },
            'Spain': {
                'weight': 4.8, 'faker': 'es_ES', 'iso_code': 'ES',
                'cities': [
                    ('Madrid', 28001, 35.0), ('Barcelona', 8001, 30.0), ('Valencia', 46001, 10.0),
                    ('Seville', 41001, 8.0), ('Bilbao', 48001, 5.0), ('Málaga', 29001, 4.0),
                    ('Palma', 7001, 3.0), ('Las Palmas', 35001, 2.5), ('Zaragoza', 50001, 2.5)
                ]
            },
            'Netherlands': {
                'weight': 3.2, 'faker': 'nl_NL', 'iso_code': 'NL',
                'cities': [
                    ('Amsterdam', 1012, 45.0), ('Rotterdam', 3011, 20.0), ('The Hague', 2511, 15.0),
                    ('Utrecht', 3511, 12.0), ('Eindhoven', 5611, 8.0)
                ]
            },
            'Turkey': {
                'weight': 2.8, 'faker': 'tr_TR', 'iso_code': 'TR',
                'cities': [
                    ('Istanbul', 34000, 50.0), ('Ankara', 6000, 20.0), ('Izmir', 35000, 15.0),
                    ('Antalya', 7000, 10.0), ('Bursa', 16000, 5.0)
                ]
            },
            'Poland': {
                'weight': 2.2, 'faker': 'pl_PL', 'iso_code': 'PL',
                'cities': [
                    ('Warsaw', 100, 35.0), ('Krakow', 30000, 20.0), ('Gdansk', 80000, 15.0),
                    ('Wroclaw', 50000, 12.0), ('Poznan', 60000, 10.0), ('Lodz', 90000, 8.0)
                ]
            },
            'Portugal': {
                'weight': 1.8, 'faker': 'pt_PT', 'iso_code': 'PT',
                'cities': [
                    ('Lisbon', 1000, 60.0), ('Porto', 4000, 25.0), ('Faro', 8000, 10.0), ('Braga', 4700, 5.0)
                ]
            },
            'Czech Republic': {
                'weight': 1.5, 'faker': 'cs_CZ', 'iso_code': 'CZ',
                'cities': [
                    ('Prague', 10000, 70.0), ('Brno', 60000, 20.0), ('Ostrava', 70000, 10.0)
                ]
            },
            'Sweden': {
                'weight': 1.4, 'faker': 'sv_SE', 'iso_code': 'SE',
                'cities': [
                    ('Stockholm', 11120, 50.0), ('Gothenburg', 41101, 25.0), ('Malmö', 21101, 15.0), ('Uppsala', 75101, 10.0)
                ]
            },
            'Norway': {
                'weight': 1.2, 'faker': 'no_NO', 'iso_code': 'NO',
                'cities': [
                    ('Oslo', 101, 60.0), ('Bergen', 5003, 20.0), ('Trondheim', 7030, 12.0), ('Stavanger', 4001, 8.0)
                ]
            },
            'Denmark': {
                'weight': 1.1, 'faker': 'da_DK', 'iso_code': 'DK',
                'cities': [
                    ('Copenhagen', 1050, 70.0), ('Aarhus', 8000, 20.0), ('Odense', 5000, 10.0)
                ]
            },
            'Finland': {
                'weight': 0.9, 'faker': 'fi_FI', 'iso_code': 'FI',
                'cities': [
                    ('Helsinki', 100, 60.0), ('Tampere', 33100, 20.0), ('Turku', 20100, 12.0), ('Oulu', 90100, 8.0)
                ]
            },
            
            # Asia-Pacific - Major economies
            'China': {
                'weight': 9.5, 'faker': 'zh_CN', 'iso_code': 'CN',
                'cities': [
                    ('Shanghai', 200001, 20.0), ('Beijing', 100001, 18.0), ('Shenzhen', 518001, 15.0),
                    ('Guangzhou', 510001, 12.0), ('Hangzhou', 310001, 8.0), ('Chengdu', 610001, 6.0),
                    ('Wuhan', 430001, 5.0), ('Xian', 710001, 4.0), ('Suzhou', 215001, 4.0),
                    ('Nanjing', 210001, 3.0), ('Tianjin', 300001, 3.0), ('Qingdao', 266001, 2.0)
                ]
            },
            'Japan': {
                'weight': 6.8, 'faker': 'ja_JP', 'iso_code': 'JP',
                'cities': [
                    ('Tokyo', 1000001, 40.0), ('Osaka', 5300001, 20.0), ('Yokohama', 2200001, 10.0),
                    ('Nagoya', 4600001, 8.0), ('Sapporo', 600001, 6.0), ('Fukuoka', 8100001, 5.0),
                    ('Kobe', 6500001, 4.0), ('Kyoto', 6000001, 4.0), ('Sendai', 9800001, 3.0)
                ]
            },
            'India': {
                'weight': 5.5, 'faker': 'hi_IN', 'iso_code': 'IN',
                'cities': [
                    ('Mumbai', 400001, 25.0), ('Delhi', 110001, 20.0), ('Bangalore', 560001, 15.0),
                    ('Hyderabad', 500001, 10.0), ('Chennai', 600001, 8.0), ('Pune', 411001, 7.0),
                    ('Kolkata', 700001, 6.0), ('Ahmedabad', 380001, 4.0), ('Gurgaon', 122001, 3.0), ('Kochi', 682001, 2.0)
                ]
            },
            'South Korea': {
                'weight': 4.2, 'faker': 'ko_KR', 'iso_code': 'KR',
                'cities': [
                    ('Seoul', 100001, 55.0), ('Busan', 600001, 20.0), ('Incheon', 400001, 12.0),
                    ('Daegu', 700001, 8.0), ('Daejeon', 300001, 5.0)
                ]
            },
            'Australia': {
                'weight': 3.8, 'faker': 'en_AU', 'iso_code': 'AU',
                'cities': [
                    ('Sydney', 2000, 35.0), ('Melbourne', 3000, 30.0), ('Brisbane', 4000, 15.0),
                    ('Perth', 6000, 10.0), ('Adelaide', 5000, 6.0), ('Canberra', 2600, 4.0)
                ]
            },
            'Thailand': {
                'weight': 2.5, 'faker': 'th_TH', 'iso_code': 'TH',
                'cities': [
                    ('Bangkok', 10100, 60.0), ('Chiang Mai', 50000, 15.0), ('Phuket', 83000, 12.0),
                    ('Pattaya', 20150, 8.0), ('Hat Yai', 90110, 5.0)
                ]
            },
            'Indonesia': {
                'weight': 2.2, 'faker': 'id_ID', 'iso_code': 'ID',
                'cities': [
                    ('Jakarta', 10110, 50.0), ('Surabaya', 60111, 15.0), ('Bandung', 40111, 12.0),
                    ('Medan', 20111, 10.0), ('Bali', 80111, 8.0), ('Semarang', 50111, 5.0)
                ]
            },
            
            # Middle East & Africa
            'Saudi Arabia': {
                'weight': 3.2, 'faker': 'ar_SA', 'iso_code': 'SA',
                'cities': [
                    ('Riyadh', 11564, 40.0), ('Jeddah', 21577, 30.0), ('Dammam', 32253, 15.0),
                    ('Mecca', 24231, 10.0), ('Medina', 42311, 5.0)
                ]
            },
            'Israel': {
                'weight': 1.8, 'faker': 'he_IL', 'iso_code': 'IL',
                'cities': [
                    ('Tel Aviv', 61000, 45.0), ('Jerusalem', 91000, 25.0), ('Haifa', 31000, 15.0),
                    ('Beersheba', 84000, 10.0), ('Netanya', 42000, 5.0)
                ]
            },
            'Egypt': {
                'weight': 1.5, 'faker': 'ar_EG', 'iso_code': 'EG',
                'cities': [
                    ('Cairo', 11511, 50.0), ('Alexandria', 21500, 25.0), ('Giza', 12511, 15.0), ('Sharm El Sheikh', 46619, 10.0)
                ]
            },
            
            # South America
            'Brazil': {
                'weight': 4.2, 'faker': 'pt_BR', 'iso_code': 'BR',
                'cities': [
                    ('São Paulo', 1310, 30.0), ('Rio de Janeiro', 20040, 25.0), ('Brasília', 70040, 12.0),
                    ('Salvador', 40070, 8.0), ('Belo Horizonte', 30112, 6.0), ('Fortaleza', 60175, 5.0),
                    ('Recife', 50010, 4.0), ('Porto Alegre', 90010, 4.0), ('Manaus', 69005, 3.0), ('Curitiba', 80010, 3.0)
                ]
            },
            
            # Eastern Europe & Russia
            'Russia': {
                'weight': 2.8, 'faker': 'ru_RU', 'iso_code': 'RU',
                'cities': [
                    ('Moscow', 101000, 45.0), ('Saint Petersburg', 190000, 25.0), ('Novosibirsk', 630000, 8.0),
                    ('Yekaterinburg', 620000, 6.0), ('Nizhny Novgorod', 603000, 5.0), ('Kazan', 420000, 4.0),
                    ('Chelyabinsk', 454000, 3.0), ('Omsk', 644000, 2.0), ('Samara', 443000, 2.0)
                ]
            }
        }
        
        # Pre-calculate normalized weights for performance
        total_weight = sum(country['weight'] for country in self.country_distribution.values())
        self.countries = list(self.country_distribution.keys())
        self.country_weights = [self.country_distribution[c]['weight'] / total_weight * 100 for c in self.countries]
        
        # Pre-calculate city weights for each country
        self.city_data = {}
        for country, data in self.country_distribution.items():
            cities = data['cities']
            city_weights = [city[2] for city in cities]
            self.city_data[country] = {
                'cities': cities,
                'weights': city_weights,
                'faker': data['faker'],
                'iso_code': data['iso_code']
            }
    
    def initialize_passport_counter(self, db_manager):
        """Initialize passport counter based on existing data"""
        try:
            with Session(db_manager.engine) as session:
                # Get the highest existing passenger_id to continue numbering
                max_id = session.exec(select(func.max(Passenger.passenger_id))).first()
                self.passport_counter = max_id if max_id else 0
                print(f"   🔢 Passport counter initialized to: {self.passport_counter}")
        except Exception:
            # If table doesn't exist or is empty, start from 0
            self.passport_counter = 0
            print(f"   🔢 Passport counter initialized to: 0 (fresh start)")
    
    def generate_passport_number(self, iso_code: str) -> str:
        """Ultra-fast passport generation with sequential numbering"""
        # Use sequential numbering for guaranteed uniqueness and speed
        self.passport_counter += 1
        # Format: ISO code + 7-digit sequential number (zero-padded)
        return f"{iso_code}{self.passport_counter:07d}"
    
    def select_country_and_city(self) -> Tuple[str, str, int, str, str]:
        """Select country and city based on pre-calculated weighted distribution"""
        # Use pre-calculated weights for faster selection
        country = random.choices(self.countries, weights=self.country_weights)[0]
        
        # Get pre-calculated city data
        city_info = self.city_data[country]
        selected_city = random.choices(city_info['cities'], weights=city_info['weights'])[0]
        city_name, base_zip, _ = selected_city
        
        # Add variation to zip codes (keep within valid range)
        max_variation = min(999, 99999 - base_zip)
        if max_variation > 0:
            zip_code = base_zip + random.randint(0, max_variation)
        else:
            zip_code = base_zip
        
        return country, city_name, zip_code, city_info['faker'], city_info['iso_code']
    
    def generate_passenger_batch(self, batch_size: int) -> Tuple[List[Dict], List[Dict]]:
        """Generate a batch of passenger records as dictionaries for bulk insert"""
        passengers = []
        passenger_details = []
        
        # Pre-calculate some values for the batch
        today = date.today()
        
        for i in range(batch_size):
            # Select geographic location
            country, city, zip_code, faker_locale, iso_code = self.select_country_and_city()
            faker = self.fakers[faker_locale]
            
            # Generate passport number with country code
            passport_no = self.generate_passport_number(iso_code)
            
            # Generate locale-appropriate names
            first_name = faker.first_name()
            last_name = faker.last_name()
            
            # Generate age using pre-calculated weights
            age = random.choices(self.age_range, weights=self.age_weights)[0]
            birth_date = today - timedelta(days=age * 365 + random.randint(0, 365))
            
            # Generate other details
            sex = random.choice(['M', 'F'])
            street = faker.street_address()
            email = faker.email() if random.random() < 0.85 else None
            phone = faker.phone_number() if random.random() < 0.75 else None
            
            # Create passenger record as dict for bulk insert
            passenger_dict = {
                'passportno': passport_no,
                'firstname': first_name,
                'lastname': last_name
            }
            
            # Create passenger details as dict (passenger_id will be set later)
            details_dict = {
                'passenger_id': None,  # Will be set after bulk insert
                'birthdate': birth_date,
                'sex': sex,
                'street': street,
                'city': city,
                'zip': zip_code,
                'country': country,
                'emailaddress': email,
                'telephoneno': phone
            }
            
            passengers.append(passenger_dict)
            passenger_details.append(details_dict)
        
        return passengers, passenger_details
    
    def generate_ultra_fast_batch(self, batch_size: int) -> Tuple[str, str, List]:
        """Generate batch data optimized for raw SQL bulk insert"""
        # Pre-calculate values
        today = date.today()
        
        # Pre-select all countries and cities for the batch
        countries = random.choices(self.countries, weights=self.country_weights, k=batch_size)
        
        passenger_values = []
        detail_values = []
        
        for i in range(batch_size):
            country = countries[i]
            city_info = self.city_data[country]
            
            # Fast city selection
            selected_city = random.choices(city_info['cities'], weights=city_info['weights'])[0]
            city_name, base_zip, _ = selected_city
            
            # Fast zip code variation
            max_variation = min(999, 99999 - base_zip)
            zip_code = base_zip + (random.randint(0, max_variation) if max_variation > 0 else 0)
            
            # Fast passport generation
            passport_no = self.generate_passport_number(city_info['iso_code'])
            
            # Fast name selection from pre-generated pools
            name_pool = self.name_pools[city_info['faker']]
            first_name = random.choice(name_pool['first_names'])
            last_name = random.choice(name_pool['last_names'])
            
            # Fast age selection
            age = random.choices(self.age_range, weights=self.age_weights)[0]
            birth_date = today - timedelta(days=age * 365 + random.randint(0, 365))
            
            # Fast other selections
            sex = random.choice(['M', 'F'])
            street = random.choice(name_pool['streets'])
            email = random.choice(name_pool['emails']) if random.random() < 0.85 else None
            phone = random.choice(name_pool['phones']) if random.random() < 0.75 else None
            
            # Build SQL values (escape single quotes)
            first_name_escaped = first_name.replace("'", "''")
            last_name_escaped = last_name.replace("'", "''")
            street_escaped = street.replace("'", "''")
            city_escaped = city_name.replace("'", "''")
            country_escaped = country.replace("'", "''")
            email_escaped = email.replace("'", "''") if email else None
            phone_escaped = phone.replace("'", "''") if phone else None
            
            passenger_values.append(f"('{passport_no}', '{first_name_escaped}', '{last_name_escaped}')")
            
            email_val = 'NULL' if email is None else f"'{email_escaped}'"
            phone_val = 'NULL' if phone is None else f"'{phone_escaped}'"
            
            detail_values.append(
                f"({i+1}, '{birth_date}', '{sex}', '{street_escaped}', '{city_escaped}', "
                f"{zip_code}, '{country_escaped}', {email_val}, {phone_val})"
            )
        
        # Build bulk INSERT statements
        passenger_sql = f"""
            INSERT INTO passenger (passportno, firstname, lastname) VALUES 
            {','.join(passenger_values)}
        """
        
        detail_sql_template = """
            INSERT INTO passengerdetails 
            (passenger_id, birthdate, sex, street, city, zip, country, emailaddress, telephoneno) VALUES 
            {}
        """
        
        return passenger_sql, detail_sql_template, detail_values
    
    def generate_passenger_batch_objects(self, batch_size: int) -> Tuple[List[Passenger], List[PassengerDetails]]:
        """Generate a batch of passenger records as SQLModel objects for reliable ID handling"""
        passengers = []
        passenger_details = []
        
        # Pre-calculate some values for the batch
        today = date.today()
        
        for i in range(batch_size):
            # Select geographic location
            country, city, zip_code, faker_locale, iso_code = self.select_country_and_city()
            faker = self.fakers[faker_locale]
            
            # Generate passport number with country code
            passport_no = self.generate_passport_number(iso_code)
            
            # Generate locale-appropriate names (force English for readability)
            if faker_locale in ['zh_CN', 'ja_JP', 'ko_KR', 'ar_SA', 'ar_EG', 'hi_IN', 'th_TH', 'he_IL']:
                # Use English faker for these locales to avoid script issues
                english_faker = self.fakers['en_US']
                first_name = english_faker.first_name()
                last_name = english_faker.last_name()
            else:
                first_name = faker.first_name()
                last_name = faker.last_name()
            
            # Generate age using pre-calculated weights
            age = random.choices(self.age_range, weights=self.age_weights)[0]
            birth_date = today - timedelta(days=age * 365 + random.randint(0, 365))
            
            # Generate other details
            sex = random.choice(['M', 'F'])
            street = faker.street_address()
            email = faker.email() if random.random() < 0.85 else None
            phone = faker.phone_number() if random.random() < 0.75 else None
            
            # Create passenger object
            passenger = Passenger(
                passportno=passport_no,
                firstname=first_name,
                lastname=last_name
            )
            
            # Create passenger details object (passenger_id will be set after passenger insert)
            details = PassengerDetails(
                passenger_id=0,  # Will be set after passenger is inserted
                birthdate=birth_date,
                sex=sex,
                street=street,
                city=city,
                zip=zip_code,
                country=country,
                emailaddress=email,
                telephoneno=phone
            )
            
            passengers.append(passenger)
            passenger_details.append(details)
        
        return passengers, passenger_details


def populate_passengers(total_records: int = 10_000_000, batch_size: int = 100_000, clear_existing: bool = False):
    """Ultra-high-performance passenger population with raw SQL bulk inserts"""
    
    print(f"⚡ Starting ULTRA-HIGH-PERFORMANCE passenger population:")
    print(f"   🎯 Target: {total_records:,} records")
    print(f"   📦 Batch size: {batch_size:,} records")
    print(f"   ⏱️  Estimated time: ~{(total_records / batch_size) * 0.5:.0f} minutes")
    
    # Initialize database and generator
    db_manager = DatabaseManager()
    
    # Use standard database manager (connection optimizations will be done at runtime)
    optimized_db = db_manager
    generator = PassengerGenerator()
    
    # Ensure tables exist
    optimized_db.create_tables()
    
    # Clear existing data if requested
    if clear_existing:
        print("   🗑️  Clearing existing data...")
        with Session(optimized_db.engine) as session:
            session.execute(text('DELETE FROM passengerdetails'))
            session.execute(text('DELETE FROM passenger'))
            session.execute(text('ALTER TABLE passenger AUTO_INCREMENT = 1'))
            session.commit()
        print("   ✅ Database cleared")
    
    # Initialize passport counter based on existing data
    generator.initialize_passport_counter(optimized_db)
    
    total_batches = (total_records + batch_size - 1) // batch_size
    records_inserted = 0
    start_time = time.time()
    
    try:
        # Use raw connection for maximum performance
        with optimized_db.engine.connect() as connection:
            # Disable autocommit and foreign key checks for speed
            if 'mysql' in str(connection.engine.url):
                connection.execute(text("SET autocommit=0"))
                connection.execute(text("SET foreign_key_checks=0"))
                connection.execute(text("SET unique_checks=0"))
                connection.execute(text("SET sql_log_bin=0"))
            
            for batch_num in range(total_batches):
                batch_start_time = time.time()
                current_batch_size = min(batch_size, total_records - records_inserted)
                
                print(f"\n⚡ Processing batch {batch_num + 1}/{total_batches} ({current_batch_size:,} records)...")
                
                # Generate ultra-fast batch with raw SQL
                passenger_sql, detail_sql_template, detail_values = generator.generate_ultra_fast_batch(current_batch_size)
                
                # Execute raw SQL for passengers
                result = connection.execute(text(passenger_sql))
                
                # Get the starting passenger_id for this batch
                # For MySQL, lastrowid gives us the first ID of the batch when using bulk insert
                first_insert_id = result.lastrowid
                
                # Update detail values with correct passenger_ids
                updated_detail_values = []
                for i, detail_template in enumerate(detail_values):
                    # Replace the placeholder passenger_id with actual ID
                    actual_detail = detail_template.replace(f"({i+1},", f"({first_insert_id + i},", 1)
                    updated_detail_values.append(actual_detail)
                
                # Execute raw SQL for details in chunks to avoid query size limits
                chunk_size = 10000  # MySQL query size limit consideration
                for chunk_start in range(0, len(updated_detail_values), chunk_size):
                    chunk_end = min(chunk_start + chunk_size, len(updated_detail_values))
                    chunk_values = updated_detail_values[chunk_start:chunk_end]
                    
                    detail_sql = detail_sql_template.format(','.join(chunk_values))
                    connection.execute(text(detail_sql))
                
                # Commit the batch
                connection.commit()
                
                records_inserted += current_batch_size
                batch_time = time.time() - batch_start_time
                
                # Performance metrics
                records_per_second = current_batch_size / batch_time if batch_time > 0 else 0
                progress = (records_inserted / total_records) * 100
                elapsed_total = time.time() - start_time
                
                if records_inserted > 0 and elapsed_total > 0:
                    avg_rate = records_inserted / elapsed_total
                    eta_seconds = (total_records - records_inserted) / avg_rate if avg_rate > 0 else 0
                    eta_minutes = eta_seconds / 60
                else:
                    eta_minutes = 0
                
                print(f"   🚀 Batch completed in {batch_time:.1f}s ({records_per_second:,.0f} records/sec)")
                print(f"   📊 Progress: {records_inserted:,}/{total_records:,} ({progress:.1f}%)")
                print(f"   ⏱️  ETA: {eta_minutes:.1f} minutes remaining")
            
            # Re-enable checks
            if 'mysql' in str(connection.engine.url):
                connection.execute(text("SET foreign_key_checks=1"))
                connection.execute(text("SET unique_checks=1"))
                connection.execute(text("SET autocommit=1"))
    
    except Exception as e:
        print(f"❌ Error during population: {e}")
        raise
    
    total_time = time.time() - start_time
    avg_rate = records_inserted / total_time if total_time > 0 else 0
    
    print(f"\n🎉 ULTRA-FAST Population completed!")
    print(f"   📈 Total records: {records_inserted:,}")
    print(f"   ⏱️  Total time: {total_time/60:.1f} minutes")
    print(f"   🚀 Average rate: {avg_rate:,.0f} records/second")
    print(f"   💾 Database size: ~{records_inserted * 200 / 1024 / 1024:.0f} MB")
    
    # Print distribution summary
    print(f"\n🌍 Geographic Distribution Summary:")
    for country, weight in zip(generator.countries, generator.country_weights):
        expected_count = int(records_inserted * weight / 100)
        print(f"   {country}: ~{expected_count:,} passengers ({weight:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Ultra-high-performance passenger population with realistic data')
    parser.add_argument('--total-records', type=int, default=10_000_000,
                       help='Total number of records to generate (default: 10,000,000)')
    parser.add_argument('--batch-size', type=int, default=100_000,
                       help='Batch size for database inserts (default: 100,000, max: 500,000)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing passenger data before starting')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.total_records <= 0:
        print("❌ Error: total-records must be positive")
        return 1
    
    if args.batch_size <= 0 or args.batch_size > 500_000:
        print("❌ Error: batch-size must be between 1 and 500,000")
        return 1
    
    try:
        populate_passengers(args.total_records, args.batch_size, args.clear)
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())