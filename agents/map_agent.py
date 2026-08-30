"""Reliable server-side geocoding for the map and form flows."""

from functools import lru_cache
import os
import requests


class MapsAgent:
    endpoint = "https://nominatim.openstreetmap.org/search"

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
        } for item in data]

    def extract_data(self, place):
        matches = self.results(place)
        return matches[0] if matches else None
