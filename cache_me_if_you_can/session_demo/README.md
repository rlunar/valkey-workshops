# Flight Session Demo - Flask with Valkey Session Storage

A Flask application demonstrating session management using Valkey (Redis-compatible) as the session storage backend.

## Features

- **Passenger Authentication**: Login using passport number (passport serves as both username and password)
- **Weather Information**: Add zip code to fetch and store weather data in session
- **Flight Management**: Browse today's flights and add them to your session
- **Valkey Session Storage**: All session data is stored in Valkey (Redis-compatible)

## Prerequisites

- Python 3.8+
- MySQL/MariaDB with flughafendb_large database
- Valkey or Redis server running on localhost:6379

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env` (in project root):
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=flughafendb_large

CACHE_HOST=localhost
CACHE_PORT=6379
```

3. Ensure Valkey/Redis is running:
```bash
# Check if Valkey is running
redis-cli ping
# Should return: PONG
```

## Running the Application

```bash
python app.py
```

The application will be available at: http://localhost:5001

## Usage

1. **Login**: Enter a valid passport number from the database (e.g., find one by querying the `passenger` table)
2. **Add Weather**: Navigate to Weather page, select country and zip code to fetch weather information
3. **Add Flights**: Browse today's flights and add them to your session
4. **Dashboard**: View all your session data including passenger info, weather, and selected flights

## Session Storage

All data is stored in Valkey with the following structure:
- Session key prefix: `flight_session:`
- Data stored: passenger info, weather data, selected flights
- Sessions persist until logout or expiration

## Database Schema

The application uses the following tables:
- `passenger`: Passenger authentication and basic info
- `passengerdetails`: Extended passenger information
- `flight`: Flight schedules and details
- `airport`: Airport information
- `airline`: Airline information

## API Integration

- **Weather Service**: Uses the mock WeatherService from `services/weather_service.py`
- Supports weather data for major cities in G20 countries

## Notes

- Passport number serves as both username and password for demo purposes
- Weather data is simulated using the WeatherService mock
- Only today's flights are displayed (limited to 50 results)
- Session data is automatically cleared on logout
