import numpy as np

from agents.map_agent import MapsAgent
from prediction_service import GroundwaterPredictor


class Pipeline:
    """The application pipeline shared by terminal and Flask entry points."""

    def __init__(self):
        self.map_agent = MapsAgent()
        self.predictor = GroundwaterPredictor()
        self._station_cache = None

    def get_location(self, place):
        location = self.map_agent.extract_data(place)
        if location is None:
            raise ValueError(f"Location not found: {place}")
        return location

    def analyze(self, place):
        return self.predictor.analyze(self.get_location(place))

    def analyze_coordinates(self, lat, lng, name=None):
        """Analyze groundwater at specific coordinates (map click flow)."""
        location = {
            "latitude": lat,
            "longitude": lng,
            "name": name or f"{lat:.4f}°N, {lng:.4f}°E",
            "address": ""
        }
        return self.predictor.analyze(location)

    def get_station_overview(self):
        """Return all monitoring stations with latest status for the map overlay.

        Computation mirrors the MAD-based anomaly detection in
        GroundwaterPredictor._decision_support so the map colours are
        consistent with the dashboard.
        """
        if self._station_cache is not None:
            return self._station_cache

        raw = self.predictor.raw
        overview = []

        for _, station in self.predictor.stations.iterrows():
            code = station["Station Code"]
            station_data = raw[raw["Station Code"] == code].sort_values(["Month", "Monitoring Date", "csv_row_index"]).drop_duplicates("Month", keep="last")

            if len(station_data) < 2:
                continue

            latest = station_data.iloc[-1]
            previous = station_data.iloc[-2]
            current_level = float(latest["Ground Water Level"])
            change = current_level - float(previous["Ground Water Level"])

            # MAD-based anomaly detection — same logic as _decision_support
            all_levels = station_data["Ground Water Level"].to_numpy(dtype=float)
            historical_changes = np.diff(all_levels)
            median_change = float(np.median(historical_changes))
            mad = float(np.median(np.abs(historical_changes - median_change)))
            robust_scale = max(1.4826 * mad, 0.05)
            anomaly_score = abs(change - median_change) / robust_scale

            if anomaly_score >= 3.5:
                status = "critical"
            elif anomaly_score >= 2.5:
                status = "alert"
            elif anomaly_score >= 2.0:
                status = "watch"
            else:
                status = "normal"

            overview.append({
                "code": code,
                "place_name": ", ".join(part for part in (str(station["Block"]).strip(), str(station["District"]).strip()) if part and part not in {"-", "nan"}),
                "district": str(station["District"]).strip(),
                "block": str(station["Block"]).strip(),
                "gp_name": str(station["GP Name"]).strip(),
                "latitude": float(station["Latitude"]),
                "longitude": float(station["Longitude"]),
                "level": round(current_level, 2),
                "change": round(change, 2),
                "anomaly_score": round(float(anomaly_score), 2),
                "status": status,
                "latest_month": latest["Month"].strftime("%b %Y"),
                "rainfall": None,
                "temperature": None,
            })

        self._station_cache = overview
        return overview
