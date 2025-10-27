import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to database
conn = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD', '')
)

cursor = conn.cursor()

# Find flight with most passengers
query = """
SELECT flight_id, SUM(passengers) as total_passengers
FROM booking 
GROUP BY flight_id 
ORDER BY total_passengers DESC 
LIMIT 1
"""

cursor.execute(query)
result = cursor.fetchone()

if result:
    flight_id, total_passengers = result
    print(f"Flight {flight_id} has the most passengers: {total_passengers}")
else:
    print("No booking data found")

cursor.close()
conn.close()
