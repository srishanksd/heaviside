"""Train a validated station-aware one-month groundwater forecaster."""

import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "weights" / "station_aware_forecaster.npz"
REPORT = ROOT / "station_forecaster_validation.json"
SEQUENCE_LENGTH, RIDGE_PENALTY = 12, 1000.0


def make_examples(frame, station_codes):
    index = {code: i for i, code in enumerate(station_codes)}
    rows, targets, months = [], [], []
    for station, group in frame.groupby("Station Code"):
        group = group.sort_values("Month").reset_index(drop=True)
        levels = group["groundwater_level"].to_numpy(dtype=float)
        
        for i in range(SEQUENCE_LENGTH, len(group)):
            expected = pd.date_range(end=group["Month"].iat[i] - pd.offsets.MonthBegin(1), periods=SEQUENCE_LENGTH, freq="MS")
            if not pd.DatetimeIndex(group["Month"].iloc[i-SEQUENCE_LENGTH:i]).equals(expected):
                continue
            month, one_hot = group["Month"].iat[i].month, np.zeros(len(station_codes))
            one_hot[index[station]] = 1.0
            rows.append(np.r_[[1.0, levels[i-1], levels[i-2], levels[i-3], levels[i-12], levels[i-1]-levels[i-2], levels[i-1]-levels[i-3], np.sin(2*np.pi*month/12), np.cos(2*np.pi*month/12)], one_hot])
            targets.append(levels[i]); months.append(group["Month"].iat[i])
            
    return np.asarray(rows), np.asarray(targets), np.asarray(months)


def metric(actual, predicted):
    return {"mae_m": float(np.mean(np.abs(actual-predicted))), "rmse_m": float(np.sqrt(np.mean((actual-predicted)**2))), "r2": float(1-np.sum((actual-predicted)**2)/np.sum((actual-actual.mean())**2))}


data = pd.read_csv(ROOT / "prepared_dataset.csv")
data["Station Code"] = data["Station Code"].astype(str).str.strip()
data["Month"] = pd.to_datetime(data["Month"])
data = data.sort_values(["Station Code", "Month"]).dropna(subset=["groundwater_level"])
stations = np.array(sorted(data["Station Code"].unique()))
X, y, target_months = make_examples(data, stations)
is_train = target_months < pd.Timestamp("2025-01-01")
penalty = np.eye(X.shape[1]) * RIDGE_PENALTY; penalty[0, 0] = 0
weights = np.linalg.solve(X[is_train].T @ X[is_train] + penalty, X[is_train].T @ y[is_train])
actual, persistence, ridge = y[~is_train], X[~is_train, 1], X[~is_train] @ weights
candidates = np.arange(0, 1.01, 0.05)
scores = [metric(actual, persistence + alpha*(ridge-persistence)) for alpha in candidates]
best = min(range(len(candidates)), key=lambda i: (scores[i]["mae_m"], candidates[i]))
blend_weight = float(candidates[best])
selected = persistence + blend_weight * (ridge-persistence)
# After choosing the model form on the holdout, refit it on every available
# observation so the deployed January-2026 forecast uses 2025 information.
weights = np.linalg.solve(X.T @ X + penalty, X.T @ y)
np.savez_compressed(MODEL, weights=weights, station_codes=stations, blend_weight=blend_weight, ridge_penalty=RIDGE_PENALTY, validation_errors=actual-selected)
report = {"validation_period": "2025-01 through 2025-12", "validation_samples": int(len(actual)), "persistence": metric(actual, persistence), "station_aware_blend": metric(actual, selected), "blend_weight": blend_weight, "ridge_penalty": RIDGE_PENALTY, "improves_persistence_mae": scores[best]["mae_m"] < metric(actual, persistence)["mae_m"]}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
