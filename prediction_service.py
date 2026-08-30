"""One source of truth for raw-data station matching and dashboard forecasts."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import torch

# from model import GroundwaterLSTM
from sequence import FEATURE_COLUMNS
from model import GroundwaterLSTM

class GroundwaterPredictor:
    """Use every valid raw Karnataka monitoring coordinate for location matching."""

    def __init__(self, project_root=None):
        self.root = Path(project_root or Path(__file__).resolve().parent)
        self.prepared = pd.read_csv(self.root / "prepared_dataset.csv")
        self.prepared["Station Code"] = self.prepared["Station Code"].astype(str).str.strip()
        self.prepared["Month"] = pd.to_datetime(self.prepared["Month"])
        self.prepared = self.prepared.sort_values(["Station Code", "Month"])

        self.raw = pd.read_csv(self.root / "karnataka_man_gw_wl_monthly_data_2021_2025.csv", low_memory=False).reset_index(names="csv_row_index")
        self.raw["Station Code"] = self.raw["Station Code"].astype(str).str.strip()
        self.raw["Monitoring Date"] = pd.to_datetime(self.raw["Monitoring Date"], dayfirst=True, errors="coerce")
        for column in ("Latitude", "Longitude", "Ground Water Level"):
            self.raw[column] = pd.to_numeric(self.raw[column], errors="coerce")
        self.raw = self.raw.dropna(subset=["Station Code", "Latitude", "Longitude", "Monitoring Date", "Ground Water Level"]).copy()
        self.raw["Month"] = self.raw["Monitoring Date"].dt.to_period("M").dt.to_timestamp()
        # This is deliberately all raw CSV stations, not the ML training subset.
        station_columns = ["Station Code", "Latitude", "Longitude", "District", "Block", "GP Name"]
        self.stations = self.raw[station_columns].drop_duplicates("Station Code").sort_values("Station Code").reset_index(drop=True)
        self.station_forecaster = self._load_station_forecaster()
        self._load_lstm()

    def _load_lstm(self):
        self.model = None
        try:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            checkpoint = torch.load(self.root / "weights" / "groundwater_lstm_best.pth", map_location=device, weights_only=False)
            if list(checkpoint["feature_columns"]) != FEATURE_COLUMNS:
                return
            self.feature_scaler, self.target_scaler, self.device = checkpoint["feature_scaler"], checkpoint["target_scaler"], device
            self.model = GroundwaterLSTM(len(FEATURE_COLUMNS), checkpoint.get("hidden_size", 128), checkpoint.get("num_layers", 2), checkpoint.get("dropout", .2)).to(device)
            self.model.load_state_dict(checkpoint["model_state_dict"]); self.model.eval()
            
            # this model is not working properly so it is commented and it's weights are used.
        except Exception:
            self.model = None

    def _load_station_forecaster(self):
        model_file, report_file = self.root / "weights" / "station_aware_forecaster.npz", self.root / "station_forecaster_validation.json"
        if not model_file.exists() or not report_file.exists(): return None
        try:
            report = json.loads(report_file.read_text(encoding="utf-8"))
            model = np.load(model_file, allow_pickle=False); codes = model["station_codes"].astype(str)
            if not report.get("improves_persistence_mae"): return None
            return {"weights": model["weights"], "index": {code: i for i, code in enumerate(codes)}, "blend": float(model["blend_weight"]), "errors": model["validation_errors"] if "validation_errors" in model.files else np.array([])}
        except (OSError, ValueError, KeyError): return None

    @staticmethod
    def _distance(latitude, longitude, latitudes, longitudes):
        latitude, longitude, latitudes, longitudes = map(np.radians, [latitude, longitude, latitudes, longitudes])
        a = np.sin((latitudes-latitude)/2)**2 + np.cos(latitude)*np.cos(latitudes)*np.sin((longitudes-longitude)/2)**2
        return 6371 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    def _history(self, code):
        records = self.raw[self.raw["Station Code"] == code].sort_values(["Month", "Monitoring Date", "csv_row_index"])
        records = records.drop_duplicates("Month", keep="last").tail(12).reset_index(drop=True)
        if len(records) != 12: raise ValueError("Nearest monitoring location does not have 12 monthly readings.")
        expected = pd.date_range(records.Month.iat[0], periods=12, freq="MS")
        if not records.Month.reset_index(drop=True).equals(pd.Series(expected)): raise ValueError("Nearest monitoring location has missing months in its latest history.")
        return records

    def _nearest(self, latitude, longitude):
        stations = self.stations.copy(); stations["distance_km"] = self._distance(latitude, longitude, stations.Latitude.to_numpy(), stations.Longitude.to_numpy())
        for _, station in stations.sort_values(["distance_km", "Station Code"]).iterrows():
            try: return station, self._history(station["Station Code"])
            except ValueError: continue
        raise ValueError("No monitoring location with a complete 12-month history was found.")

    def _trained_prediction(self, code, prepared):
        model = self.station_forecaster
        if model is None or code not in model["index"] or len(prepared) != 12: return None
        levels = prepared.groundwater_level.to_numpy(float); target_month = (prepared.Month.iat[-1] + pd.DateOffset(months=1)).month
        one_hot = np.zeros(len(model["index"])); one_hot[model["index"][code]] = 1
        x = np.r_[[1, levels[-1], levels[-2], levels[-3], levels[-12], levels[-1]-levels[-2], levels[-1]-levels[-3], np.sin(2*np.pi*target_month/12), np.cos(2*np.pi*target_month/12)], one_hot]
        ridge = float(x @ model["weights"])
        return float(levels[-1] + model["blend"] * (ridge-levels[-1]))

    def _lstm_prediction(self, prepared):
        """Return a true LSTM forecast only for a complete compatible sequence."""
        if self.model is None or len(prepared) != 12:
            return None
        try:
            features = prepared[FEATURE_COLUMNS].to_numpy(dtype=float)
            scaled = self.feature_scaler.transform(features)
            tensor = torch.tensor(scaled, dtype=torch.float32, device=self.device).unsqueeze(0)
            with torch.no_grad():
                scaled_prediction = self.model(tensor).detach().cpu().numpy().reshape(-1, 1)
            return float(self.target_scaler.inverse_transform(scaled_prediction)[0, 0])
        except (KeyError, ValueError, RuntimeError):
            return None

    @staticmethod
    def _directional_baseline(levels):
        """Damped recent trend that retains decreasing water levels."""
        changes = np.diff(levels[-6:])
        change = 0.60 * float(np.median(changes)) + 0.40 * float(changes[-1])
        return float(levels[-1] + np.clip(change, -2.0, 2.0))

    def _environment_record(self, latitude, longitude, month):
        """Find the closest environmental record from the matching month."""
        candidates = self.prepared[self.prepared["Month"] == month]
        if candidates.empty:
            candidates = self.prepared
        distances = self._distance(latitude, longitude, candidates.Latitude.to_numpy(float), candidates.Longitude.to_numpy(float))
        return candidates.iloc[int(np.argmin(distances))]

    @staticmethod
    def _number_or_none(value):
        return None if pd.isna(value) else float(value)

    def _support(self, code, levels, prediction, rainfall=None):
        changes = np.diff(levels); typical = float(np.median(changes)); scale = max(float(np.median(abs(changes-typical))*1.4826), .05)
        observed = float(changes[-1]); score = abs(observed-typical)/scale
        anomaly = "high" if score >= 3.5 else ("moderate" if score >= 2.5 else "normal")
        change = prediction-levels[-1]; errors = self.station_forecaster["errors"] if self.station_forecaster else []
        probability = None if len(errors) == 0 else round(100*float(np.mean(errors > -change if change > .05 else (errors < -change if change < -.05 else abs(errors) <= .1))), 1)
        label = "forecast-direction probability" if abs(change) > .05 else "near-stability probability (±0.10 m)"
        percentile = 100*float(np.mean(levels <= levels[-1])); priority_score = min(100, round(.55*percentile + 8*min(score,5) + (10 if change > 0 else 0))); priority = "high" if priority_score >= 75 else ("moderate" if priority_score >= 45 else "routine")
        government=["Continue automated monthly ingestion and station-level review."]
        people=["Record the local well level on the same day each month to corroborate the monitoring station."]
        if anomaly != "normal": government.insert(0,"Verify the unusual reading with a field measurement before operational action."); people.insert(0,"Avoid changing pumping from one unusual monthly reading without a local check.")
        if priority != "routine": government.append("Prioritize this area for monitoring, demand review, and recharge assessment."); people.append("Schedule irrigation from soil-moisture and weather observations; avoid routine over-irrigation.")
        if rainfall is not None and rainfall < 20: people.append("Recent rainfall is low; use local water-saving irrigation practices where appropriate.")
        return {"probability_percent":probability,"probability_label":label,"anomaly_score":round(score,2),"anomaly_level":anomaly,"anomaly_text":f"{anomaly.title()} month-to-month anomaly: {observed:+.2f} m versus a typical {typical:+.2f} m change.","priority_score":priority_score,"priority":priority,"government_guidance":government,"community_guidance":people}

    def analyze(self, location):
        latitude, longitude = float(location["latitude"]), float(location["longitude"])
        station, raw_history = self._nearest(latitude, longitude); code = station["Station Code"]
        prepared = self.prepared[(self.prepared["Station Code"] == code) & (self.prepared.Month.isin(raw_history.Month))].sort_values("Month")
        trained = len(prepared) == 12 and np.allclose(prepared.groundwater_level.to_numpy(float), raw_history["Ground Water Level"].to_numpy(float))
        levels = raw_history["Ground Water Level"].to_numpy(float); current = float(levels[-1])
        environmental_rows = prepared if trained else pd.DataFrame([
            self._environment_record(latitude, longitude, row.Month)
            for row in raw_history.itertuples()
        ])
        prediction = self._trained_prediction(code, prepared) if trained else None
        if prediction is None:
            prediction = self._directional_baseline(levels)
            method = "Raw-history directional trend (nearest station)"
        else: method = "Validated station-aware forecast"
        lstm_prediction = self._lstm_prediction(environmental_rows) if trained else None
        weather = [{"month":row.Month.strftime("%b %Y"),"temperature_c":self._number_or_none(row.temperature_c),"rainfall_mm":self._number_or_none(row.rainfall_mm)} for row in environmental_rows.itertuples()]
        rainfall = weather[-1]["rainfall_mm"]
        support = self._support(code, levels, prediction, rainfall)
        records = raw_history.to_dict("records")
        history=[{"month":row["Month"].strftime("%b %Y"),"groundwater":float(row["Ground Water Level"])} for row in records]
        csv_rows=[{"csv_row_index":int(row["csv_row_index"]),"monitoring_date":row["Monitoring Date"].strftime("%Y-%m-%d"),"groundwater_level":float(row["Ground Water Level"])} for row in records]
        last = environmental_rows.iloc[-1]
        change = prediction-current
        feature_source = "Station-matched training features" if trained else "Nearest time-matched environmental dataset record"
        return {"location":{"name":location.get("name","Searched location"),"address":location.get("address", ""),"latitude":latitude,"longitude":longitude},"station":{"code":code,"latitude":float(station.Latitude),"longitude":float(station.Longitude),"district":station.District,"block":station.Block,"gp_name":station["GP Name"],"distance_km":float(station.distance_km)},"current_groundwater":current,"prediction":prediction,"lstm_prediction":lstm_prediction,"change":change,"prediction_status":"approximately stable" if abs(change)<.1 else ("increase" if change>0 else "decrease"),"forecast_method":method,"forecast_version":4,"decision_support":support,"history":history,"weather_history":weather,"temperature":self._number_or_none(last.temperature_c),"rainfall":rainfall,"soil_ph":self._number_or_none(last.soil_ph),"clay":self._number_or_none(last.clay_percent),"sand":self._number_or_none(last.sand_percent),"silt":self._number_or_none(last.silt_percent),"organic_carbon":self._number_or_none(last.organic_carbon),"nitrogen":self._number_or_none(last.nitrogen),"elevation":self._number_or_none(last.elevation_m),"chart":{"dates":[x["month"] for x in history],"values":[x["groundwater"] for x in history],"forecast_date":(raw_history.Month.iat[-1]+pd.DateOffset(months=1)).strftime("%b %Y"),"forecast_value":prediction},"data_provenance":{"groundwater":"Selected station's raw CSV rows","features":feature_source,"raw_csv_rows":csv_rows}}
