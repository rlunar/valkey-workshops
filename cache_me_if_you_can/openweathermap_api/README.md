# OpenWeatherMap One Call API 4.0 Proxy

A small Flask API that proxies requests to the [OpenWeatherMap One Call API 4.0](https://openweathermap.org/api/one-call-4). It keeps the OpenWeatherMap API key on the server, validates common request parameters, and returns upstream JSON responses to callers.

## Requirements

- Python 3.13 or later
- Dependencies installed with `uv sync`
- An OpenWeatherMap API key with access to One Call API 4.0

Run commands in this document from the `cache_me_if_you_can` directory.

## Configuration

Add the API key to `cache_me_if_you_can/.env`:

```dotenv
OPENWEATHERMAP_API_KEY=your_api_key
```

The service also recognizes `OPENWEATHER_API_KEY` and `OWM_API_KEY`, but `OPENWEATHERMAP_API_KEY` is the preferred name.

Optional settings:

```dotenv
OPENWEATHERMAP_BASE_URL=https://api.openweathermap.org/data/4.0/onecall
OPENWEATHERMAP_TIMEOUT_SECONDS=10
OPENWEATHERMAP_API_HOST=127.0.0.1
OPENWEATHERMAP_API_PORT=5000
FLASK_DEBUG=false
```

Never commit `.env` or expose the API key to clients. The proxy ignores any caller-provided `appid` parameter and always uses its server-side key.

## Start the API

```bash
uv run python -m openweathermap_api
```

The service listens on `http://127.0.0.1:5000` by default.

## Endpoints

### Service information

```http
GET /
```

Returns the service name and available endpoint patterns.

### Health check

```http
GET /health
```

Example response:

```json
{
  "openweathermap_configured": true,
  "status": "ok"
}
```

The health endpoint does not make an upstream request. `openweathermap_configured` only indicates whether an API key was loaded.

### Current weather

```http
GET /current?lat={latitude}&lon={longitude}
```

Example:

```bash
curl "http://127.0.0.1:5000/current?lat=33.44&lon=-94.04&units=metric&lang=en"
```

### Weather timelines

```http
GET /timeline/{interval}?lat={latitude}&lon={longitude}
```

Supported intervals:

- `1min`
- `15min`
- `1h`
- `1day`

Example:

```bash
curl "http://127.0.0.1:5000/timeline/1h?lat=33.44&lon=-94.04&units=imperial"
```

### Weather alert details

```http
GET /alert/{alert_id}
```

Example:

```bash
curl "http://127.0.0.1:5000/alert/example-alert-id"
```

Use an alert identifier returned by another One Call endpoint.

## Query parameters

Location endpoints require:

| Parameter | Description |
| --- | --- |
| `lat` | Latitude from `-90` through `90` |
| `lon` | Longitude from `-180` through `180` |

Common optional parameters:

| Parameter | Description |
| --- | --- |
| `units` | `standard`, `metric`, or `imperial` |
| `lang` | OpenWeatherMap localization language code |

Additional query parameters are forwarded to OpenWeatherMap, except `appid`.

## Errors

Errors use JSON responses:

```json
{
  "error": "Description of the error"
}
```

Validation failures return HTTP `400`. Missing server configuration returns `503`. Network failures and invalid upstream responses return `502`. OpenWeatherMap client errors such as `401`, `404`, or `429` retain their upstream status and include upstream error details.

## Package structure

```text
openweathermap_api/
├── __init__.py   # Public package exports
├── __main__.py   # python -m entry point
├── app.py        # Flask application and routes
├── client.py     # OpenWeatherMap HTTP client
└── README.md
```

## Validation

Compile the package and run the project test suite:

```bash
uv run python -m compileall -q openweathermap_api
uv run pytest -q
```
