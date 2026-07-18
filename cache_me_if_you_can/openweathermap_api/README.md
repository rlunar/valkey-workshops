# OpenWeatherMap One Call API 4.0 Proxy

A Flask proxy for the [OpenWeatherMap One Call API 4.0](https://openweathermap.org/api/one-call-4) with server-side API key handling, Valkey JSON cache-aside behavior, request timing, and safety-gated namespaced cache clearing.

## Run

From `cache_me_if_you_can`:

```bash
uv run python -m openweathermap_api
```

The service listens on `http://127.0.0.1:5000` by default. Configure `OPENWEATHERMAP_API_KEY` in `.env`; the repository `quickstart.sh` starts the JSON-enabled Valkey bundle on port `16379`.

## Python clients

The package exports two clients for direct use by other modules:

```python
from openweathermap_api import (
    OpenWeatherMapClient,
    OpenWeatherMapGeocodingClient,
)
```

`OpenWeatherMapClient` reads One Call weather data. `OpenWeatherMapGeocodingClient.search()` resolves worldwide city queries through the Direct Geocoding API and can cache results independently under `openweathermap:geocoding:v1:cache:v1:response:*`. The API key is sent upstream but excluded from cache identity.

Geocoding settings include:

```dotenv
OPENWEATHERMAP_GEOCODING_BASE_URL=https://api.openweathermap.org/geo/1.0/direct
OPENWEATHERMAP_GEOCODING_CACHE_ENABLED=true
OPENWEATHERMAP_GEOCODING_CACHE_HOST=localhost
OPENWEATHERMAP_GEOCODING_CACHE_PORT=16379
OPENWEATHERMAP_GEOCODING_CACHE_DB=0
OPENWEATHERMAP_GEOCODING_CACHE_TTL_SECONDS=86400
```

Inspect cached geocoding metadata without blocking Valkey:

```bash
valkey-cli -p 16379 --scan \
  --pattern 'openweathermap:geocoding:v1:cache:v1:response:*'
```

## Endpoints

```text
GET    /health
GET    /current?lat={latitude}&lon={longitude}
GET    /timeline/{1min|15min|1h|1day}?lat={latitude}&lon={longitude}
GET    /alert/{alert_id}
DELETE /cache
```

Every JSON response includes `total_time_ms`; every response also includes `X-Total-Time-Ms` and `Server-Timing` headers.

## Cache

Responses are stored as Valkey JSON documents under versioned keys:

```text
openweathermap:onecall:v4:cache:v1:response:<resource>:location:{<lat>,<lon>}:query:<sha256>
```

Inspect them without blocking Valkey:

```bash
valkey-cli -p 16379 --scan \
  --pattern 'openweathermap:onecall:v4:cache:v1:response:*'
```

Select and inspect one item:

```bash
SAMPLE_KEY="$(valkey-cli -p 16379 --scan \
  --pattern 'openweathermap:onecall:v4:cache:v1:response:*' | head -n 1)"
valkey-cli -p 16379 JSON.GET "$SAMPLE_KEY" '$' | jq -C .
valkey-cli -p 16379 TTL "$SAMPLE_KEY"
```

Cache failures are fail-open, and only successful upstream responses are cached. `DELETE /cache` is disabled unless `OPENWEATHERMAP_CACHE_ALLOW_CLEAR=true`; when enabled, it unlinks only this namespace.

## Relative-date examples

Yesterday in New York City, beginning at local midnight:

```bash
NYC_YESTERDAY_START="$(python3 -c '
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
zone = ZoneInfo("America/New_York")
yesterday = datetime.now(zone).date() - timedelta(days=1)
print(int(datetime.combine(yesterday, time.min, tzinfo=zone).timestamp()))
')"
curl "http://127.0.0.1:5000/timeline/1h?lat=40.7128&lon=-74.0060&units=metric&start=${NYC_YESTERDAY_START}" | jq -C .
```

Tomorrow in Lima, Peru:

```bash
curl "http://127.0.0.1:5000/timeline/1day?lat=-12.0464&lon=-77.0428&units=metric" | jq -C .
```

The daily response contains a `data` array whose `dt` values can be converted to `America/Lima` to select tomorrow's local date.

## Validation

```bash
uv run python -m compileall -q openweathermap_api
uv run pytest -q
```
