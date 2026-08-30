"""Reliable server-side geocoding for the map and form flows."""

from functools import lru_cache
import os
import requests


class MapsAgent:
    endpoint = "https://nominatim.openstreetmap.org/search"
    reverse_endpoint = "https://nominatim.openstreetmap.org/reverse"
    elevation_endpoint = "https://api.open-meteo.com/v1/elevation"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": os.environ.get("NOMINATIM_USER_AGENT", "HeavisideGroundwater/1.0 (deployment-contact-required)"),
            "Accept": "application/json",
        })

    @lru_cache(maxsize=256)
    def search(self, place):
        query = " ".join(str(place).split())
        if len(query) < 2:
            return []
        response = self.session.get(
            self.endpoint,
            params={"q": query, "format": "jsonv2", "limit": 5, "addressdetails": 1, "countrycodes": "in"},
            timeout=(5, 20),
        )
        response.raise_for_status()
        return response.json()

    def results(self, place):
        try:
            data = self.search(place)
        except requests.RequestException as error:
            raise ValueError("Location search is temporarily unavailable. Please retry or choose a map station.") from error
        return [{
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "name": item.get("name") or item["display_name"].split(",")[0],
            "address": item.get("display_name", ""),
            "state": item.get("address", {}).get("state", ""),
        } for item in data]

    def extract_data(self, place):
        matches = self.results(place)
        return matches[0] if matches else None

    @lru_cache(maxsize=512)
    def state_at(self, latitude, longitude):
        """Resolve the state for a coordinate before analysing it."""
        try:
            response = self.session.get(
                self.reverse_endpoint,
                params={"lat": round(float(latitude), 5), "lon": round(float(longitude), 5), "format": "jsonv2", "addressdetails": 1, "zoom": 5},
                timeout=(5, 20),
            )
            response.raise_for_status()
            return response.json().get("address", {}).get("state", "")
        except requests.RequestException as error:
            raise ValueError("Location verification is temporarily unavailable. Please retry.") from error

    def require_karnataka(self, location):
        """Reject locations outside the project's Karnataka monitoring scope."""
        state = location.get("state") or self.state_at(location["latitude"], location["longitude"])
        if "karnataka" not in str(state).casefold():
            raise ValueError("Location outside Karnataka.")
        location["state"] = state
        return location

    @lru_cache(maxsize=512)
    def elevation(self, latitude, longitude):
        """Return terrain elevation for the exact requested coordinate in metres."""
        try:
            response = self.session.get(
                self.elevation_endpoint,
                params={"latitude": round(float(latitude), 5), "longitude": round(float(longitude), 5)},
                timeout=(5, 20),
            )
            response.raise_for_status()
            values = response.json().get("elevation", [])
            return float(values[0]) if values else None
        except (requests.RequestException, ValueError, TypeError, IndexError):
            return None
