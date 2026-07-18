"""HTTP client for OpenWeatherMap One Call API 4.0."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests


DEFAULT_BASE_URL = "https://api.openweathermap.org/data/4.0/onecall"


class OpenWeatherMapError(Exception):
    """An error that can be returned safely by the local API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class OpenWeatherMapClient:
    """Minimal client for the OpenWeatherMap One Call API 4.0 endpoints."""

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    @property
    def is_configured(self) -> bool:
        """Return whether an API key was supplied."""
        return bool(self.api_key)

    def current(self, params: dict[str, Any]) -> Any:
        """Fetch current conditions for a location."""
        return self._get("current", params)

    def timeline(self, interval: str, params: dict[str, Any]) -> Any:
        """Fetch a weather timeline at the requested interval."""
        return self._get(f"timeline/{interval}", params)

    def alert(self, alert_id: str) -> Any:
        """Fetch details for an alert returned by another endpoint."""
        encoded_alert_id = quote(alert_id, safe="")
        return self._get(f"alert/{encoded_alert_id}", {})

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        if not self.api_key:
            raise OpenWeatherMapError(
                "OpenWeatherMap API key is not configured",
                status_code=503,
            )

        request_params = {
            key: value
            for key, value in params.items()
            if value is not None and key.lower() != "appid"
        }
        request_params["appid"] = self.api_key

        try:
            response = self.session.get(
                f"{self.base_url}/{path}",
                params=request_params,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as error:
            raise OpenWeatherMapError(
                "Unable to reach OpenWeatherMap",
                status_code=502,
            ) from error

        try:
            payload = response.json()
        except ValueError as error:
            raise OpenWeatherMapError(
                "OpenWeatherMap returned an invalid response",
                status_code=502,
                details={"upstream_status": response.status_code},
            ) from error

        if not response.ok:
            status_code = response.status_code if response.status_code < 500 else 502
            raise OpenWeatherMapError(
                "OpenWeatherMap request failed",
                status_code=status_code,
                details={
                    "upstream_status": response.status_code,
                    "upstream_error": payload,
                },
            )

        return payload
