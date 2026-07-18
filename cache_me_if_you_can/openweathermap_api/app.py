"""Flask API proxy for OpenWeatherMap One Call API 4.0."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from openweathermap_api.client import (
    DEFAULT_BASE_URL,
    OpenWeatherMapClient,
    OpenWeatherMapError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

TIMELINE_INTERVALS = frozenset({"1min", "15min", "1h", "1day"})
VALID_UNITS = frozenset({"standard", "metric", "imperial"})


def _api_key_from_environment() -> str | None:
    return (
        os.getenv("OPENWEATHERMAP_API_KEY")
        or os.getenv("OPENWEATHER_API_KEY")
        or os.getenv("OWM_API_KEY")
    )


def _timeout_from_environment() -> float:
    raw_timeout = os.getenv("OPENWEATHERMAP_TIMEOUT_SECONDS", "10")
    try:
        timeout = float(raw_timeout)
    except ValueError as error:
        raise RuntimeError(
            "OPENWEATHERMAP_TIMEOUT_SECONDS must be a number"
        ) from error

    if timeout <= 0:
        raise RuntimeError("OPENWEATHERMAP_TIMEOUT_SECONDS must be greater than zero")
    return timeout


def _request_params() -> dict[str, Any]:
    params: dict[str, Any] = request.args.to_dict(flat=True)
    params.pop("appid", None)
    return params


def _validated_location_params() -> dict[str, Any]:
    params = _request_params()
    missing = [name for name in ("lat", "lon") if not params.get(name)]
    if missing:
        raise OpenWeatherMapError(
            f"Missing required query parameter(s): {', '.join(missing)}",
            status_code=400,
        )

    try:
        latitude = float(params["lat"])
        longitude = float(params["lon"])
    except (TypeError, ValueError) as error:
        raise OpenWeatherMapError(
            "lat and lon must be numbers",
            status_code=400,
        ) from error

    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise OpenWeatherMapError(
            "lat must be between -90 and 90",
            status_code=400,
        )
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise OpenWeatherMapError(
            "lon must be between -180 and 180",
            status_code=400,
        )

    units = params.get("units")
    if units:
        units = units.lower()
        if units not in VALID_UNITS:
            raise OpenWeatherMapError(
                "units must be one of: standard, metric, imperial",
                status_code=400,
            )
        params["units"] = units

    params["lat"] = latitude
    params["lon"] = longitude
    return params


def create_app(client: OpenWeatherMapClient | None = None) -> Flask:
    """Create the Flask application, optionally with an injected client."""
    app = Flask(__name__)
    weather_client = client or OpenWeatherMapClient(
        _api_key_from_environment(),
        base_url=os.getenv("OPENWEATHERMAP_BASE_URL", DEFAULT_BASE_URL),
        timeout_seconds=_timeout_from_environment(),
    )
    app.extensions["openweathermap_client"] = weather_client

    @app.errorhandler(OpenWeatherMapError)
    def handle_openweathermap_error(error: OpenWeatherMapError):
        body: dict[str, Any] = {"error": error.message}
        if error.details is not None:
            body["details"] = error.details
        return jsonify(body), error.status_code

    @app.get("/")
    def index():
        return jsonify(
            {
                "name": "OpenWeatherMap One Call API 4.0 proxy",
                "endpoints": [
                    "/health",
                    "/current?lat={latitude}&lon={longitude}",
                    "/timeline/{1min|15min|1h|1day}?lat={latitude}&lon={longitude}",
                    "/alert/{alert_id}",
                ],
            }
        )

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "openweathermap_configured": weather_client.is_configured,
            }
        )

    @app.get("/current")
    def current_weather():
        return jsonify(weather_client.current(_validated_location_params()))

    @app.get("/timeline/<interval>")
    def weather_timeline(interval: str):
        if interval not in TIMELINE_INTERVALS:
            raise OpenWeatherMapError(
                "interval must be one of: 1min, 15min, 1h, 1day",
                status_code=400,
            )
        return jsonify(
            weather_client.timeline(interval, _validated_location_params())
        )

    @app.get("/alert/<alert_id>")
    def weather_alert(alert_id: str):
        return jsonify(weather_client.alert(alert_id))

    return app


app = create_app()


def main() -> None:
    """Run the development server."""
    host = os.getenv("OPENWEATHERMAP_API_HOST", "127.0.0.1")
    port = int(os.getenv("OPENWEATHERMAP_API_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
