# Weather API Cache Demo - Verbose Mode

## Overview
Verbose mode (`--verbose` or `-v`) provides detailed information about cache operations, including cache keys, latency details, and JSON samples of API responses.

## Activation
```bash
# Enable verbose mode
.venv/bin/python samples/demo_weather_api_cache.py --verbose

# Short form
.venv/bin/python samples/demo_weather_api_cache.py -v

# Combined with other options
.venv/bin/python samples/demo_weather_api_cache.py -v -i -c 5
```

## Verbose Mode Features

### 1. Progress Bars with tqdm
In verbose mode, you'll see real-time progress bars:
```
Fetching weather: 100%|████████████████| 10/10 [00:05<00:00,  1.89city/s, New York - 245.123ms]
```

### 2. Detailed Per-City Information

#### Without Cache (Direct API Calls)
```
─── City #1: Miami ───
API Call: Direct (no cache)
Latency: 425.123ms
☀️ Miami                🇺🇸 US - 69.5°F (feels 74.9°F), clear sky

─── Sample Weather API Response (JSON) ───
╭─ Weather Data Structure ─────────────────────────────────────╮
│ {                                                             │
│   "coord": {                    ← Syntax highlighted in color│
│     "lon": -80.1918,            ← Keys in cyan               │
│     "lat": 25.7617              ← Numbers in magenta         │
│   },                            ← Strings in green           │
│   "weather": [                                                │
│     {                                                         │
│       "id": 800,                                              │
│       "main": "Clear",                                        │
│       "description": "clear sky",                             │
│       "icon": "01d"                                           │
│     }                                                         │
│   ],                                                          │
│   "base": "stations",                                         │
│   "main": {                                                   │
│     "temp": 69.5,                                             │
│     "feels_like": 74.9,                                       │
│     "temp_min": 65.2,                                         │
│     "temp_max": 73.8,                                         │
│     "pressure": 1015,                                         │
│     "humidity": 68,                                           │
│     "sea_level": 1016,                                        │
│     "grnd_level": 1012                                        │
│   },                                                          │
│   "visibility": 9500,                                         │
│   "wind": {                                                   │
│     "speed": 8.5,                                             │
│     "deg": 120,                                               │
│     "gust": 12.3                                              │
│   },                                                          │
│   "clouds": {                                                 │
│     "all": 15                                                 │
│   },                                                          │
│   "dt": 1732464000,                                           │
│   "sys": {                                                    │
│     "type": 2,                                                │
│     "id": 2045678,                                            │
│     "country": "US",                                          │
│     "sunrise": 1732442400,                                    │
│     "sunset": 1732485600                                      │
│   },                                                          │
│   "timezone": -18000,                                         │
│   "id": 4567890,                                              │
│   "name": "Miami",                                            │
│   "cod": 200                                                  │
│ }                                                             │
╰───────────────────────────────────────────────────────────────╯
```

#### With Cache (Run #1 - Populating)
```
─── City #1: Miami ───
Cache Key: weather:us:33101
Status: CACHE MISS (populated)
Latency: 425.123ms
⚡ Miami                🇺🇸 US

─── Sample Weather API Response (JSON) ───
╭─ Weather Data Structure ─────────────────────────────────────╮
│ {                                                             │
│   "coord": { ... },                                           │
│   "weather": [ ... ],                                         │
│   ...                                                         │
│ }                                                             │
╰───────────────────────────────────────────────────────────────╯
```

#### With Cache (Run #2 - Using Cache)
```
─── City #1: Miami ───
Cache Key: weather:us:33101
Status: CACHE HIT
Latency: 2.345ms
✓ ☀️ Miami                🇺🇸 US - 69.5°F (feels 74.9°F), clear sky

─── City #2: Cape Town ───
Cache Key: weather:za:8001
Status: CACHE HIT
Latency: 1.987ms
✓ 🌧️ Cape Town            🇿🇦 ZA - 82.5°F (feels 58.6°F), light rain

─── City #3: Los Angeles ───
Cache Key: weather:us:90001
Status: CACHE HIT
Latency: 1.876ms
✓ 🌨️ Los Angeles          🇺🇸 US - 65.5°F (feels 63.6°F), light snow
```

### 3. Cache Key Format
Verbose mode shows the exact cache key used for each city:
```
Cache Key: weather:<country>:<zip>
```

Examples:
- `weather:us:10001` (New York, USA)
- `weather:mx:06000` (Mexico City, Mexico)
- `weather:gb:sw1a` (London, UK)
- `weather:jp:1000001` (Tokyo, Japan)

### 4. Status Information
Detailed status for each operation:
- **CACHE HIT**: Data retrieved from cache
- **CACHE MISS (populated)**: Data fetched from API and stored in cache
- **CACHE HIT (after lock)**: Data found in cache after acquiring lock
- **LOCK WAIT**: Waiting for another process to populate cache
- **CACHE HIT (waited X.Xs)**: Data retrieved after waiting for lock
- **CACHE MISS (timeout)**: Lock timeout, fetched from API anyway

### 5. JSON Sample Display with Syntax Highlighting
The first API call in each phase shows the complete JSON structure with beautiful syntax highlighting:
- **Weather Data Structure**: Full OpenWeatherMap API response
- **Syntax Highlighted**: Uses Rich's Syntax class with Monokai theme
  - Keys in cyan
  - Strings in green
  - Numbers in magenta
  - Booleans in purple
  - Null values in red
- **Formatted with indentation**: Easy to read
- **Shows all fields**: coord, weather, main, wind, clouds, sys, etc.
- **Professional appearance**: Color-coded for better readability

## Comparison: Normal vs Verbose Mode

### Normal Mode Output
```
FETCHING WITH CACHE (Run #2)

  ✓  1. ☀️ Miami                🇺🇸 US - 69.5°F (feels 74.9°F), clear sky -  0.425ms [CACHE HIT]
  ✓  2. 🌧️ Cape Town            🇿🇦 ZA - 82.5°F (feels 58.6°F), light rain -  0.339ms [CACHE HIT]
  ✓  3. 🌨️ Los Angeles          🇺🇸 US - 65.5°F (feels 63.6°F), light snow -  0.330ms [CACHE HIT]
```

### Verbose Mode Output
```
FETCHING WITH CACHE (Run #2)

Run #2: 100%|████████████████| 10/10 [00:00<00:00, 1234.56city/s, Miami - CACHE HIT]

─── City #1: Miami ───
Cache Key: weather:us:33101
Status: CACHE HIT
Latency: 0.425ms
✓ ☀️ Miami                🇺🇸 US - 69.5°F (feels 74.9°F), clear sky

─── City #2: Cape Town ───
Cache Key: weather:za:8001
Status: CACHE HIT
Latency: 0.339ms
✓ 🌧️ Cape Town            🇿🇦 ZA - 82.5°F (feels 58.6°F), light rain

─── City #3: Los Angeles ───
Cache Key: weather:us:90001
Status: CACHE HIT
Latency: 0.330ms
✓ 🌨️ Los Angeles          🇺🇸 US - 65.5°F (feels 63.6°F), light snow
```

## Use Cases for Verbose Mode

### 1. Debugging
- See exact cache keys being used
- Verify cache hit/miss behavior
- Check latency for each operation
- Inspect API response structure

### 2. Learning
- Understand cache-aside pattern mechanics
- See how distributed locking works
- Learn OpenWeatherMap API format
- Study cache key generation

### 3. Performance Analysis
- Compare latencies between cache hits and misses
- Identify slow operations
- Monitor cache efficiency
- Track lock wait times

### 4. Development
- Verify cache key format
- Test cache invalidation
- Debug cache stampede prevention
- Validate API responses

## Tips for Using Verbose Mode

1. **Start with fewer cities**: Use `-c 5` to reduce output volume
2. **Combine with interactive**: Use `-i -v` to step through each phase
3. **Redirect output**: Save verbose output to file for analysis
4. **Focus on first call**: The JSON sample appears only for the first city
5. **Watch progress bars**: Real-time feedback on operation progress

## Example Commands

```bash
# Basic verbose mode
.venv/bin/python samples/demo_weather_api_cache.py -v

# Verbose with 5 cities
.venv/bin/python samples/demo_weather_api_cache.py -v -c 5

# Verbose + interactive + flush
.venv/bin/python samples/demo_weather_api_cache.py -v -i -f

# Verbose with custom TTL
.venv/bin/python samples/demo_weather_api_cache.py -v -t 30 -c 10

# Save verbose output to file
.venv/bin/python samples/demo_weather_api_cache.py -v > weather_demo_verbose.log 2>&1
```

## Benefits

- **Transparency**: See exactly what's happening under the hood
- **Education**: Learn cache patterns through detailed output
- **Debugging**: Identify issues quickly with detailed logs
- **Verification**: Confirm cache behavior matches expectations
- **Documentation**: JSON samples show API structure clearly
