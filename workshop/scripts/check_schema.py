import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD', '')
)

cursor = conn.cursor()

# Check if booking table exists and its structure
cursor.execute("SHOW TABLES LIKE 'booking'")
if cursor.fetchone():
    print("BOOKING TABLE STRUCTURE:")
    cursor.execute("DESCRIBE booking")
    for row in cursor.fetchall():
        print(f"  {row[0]} - {row[1]}")
    
    print("\nSAMPLE DATA:")
    cursor.execute("SELECT * FROM booking LIMIT 3")
    for row in cursor.fetchall():
        print(f"  {row}")
else:
    print("No 'booking' table found. Available tables:")
    cursor.execute("SHOW TABLES")
    for table in cursor.fetchall():
        print(f"  {table[0]}")

cursor.close()
conn.close()
