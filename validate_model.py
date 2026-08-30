"""Reproducible chronological validation, including the persistence baseline."""

import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from model import GroundwaterLSTM
from sequence import FEATURE_COLUMNS, create_sequences


ROOT = Path(__file__).resolve().parent

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

df = pd.read_csv(ROOT/"prepared_dataset.csv")
df["Month"] = pd.to_datetime(df["Month"])
df = df.sort_values(["Station Code", "Month"]).dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)

dates = np.array(sorted(df["Month"].unique()))
validation_start = dates[int(len(dates) * 0.80)]
checkpoint = torch.load(ROOT/"weights"/"groundwater_lstm_best.pth", map_location=device, weights_only=False)
checkpoint_hash = hashlib.sha256((ROOT/"weights"/"groundwater_lstm_best.pth").read_bytes()).hexdigest()

if list(checkpoint["feature_columns"]) != FEATURE_COLUMNS:
    raise ValueError("Checkpoint feature order does not match the validation feature order.")

train = df[df["Month"] < validation_start].copy()
validation = df[df["Month"] >= validation_start].copy()
feature_scaler, target_scaler = checkpoint["feature_scaler"], checkpoint["target_scaler"]

for frame in (train, validation):
    frame[FEATURE_COLUMNS] = feature_scaler.transform(frame[FEATURE_COLUMNS])
    frame[["groundwater_level"]] = target_scaler.transform(frame[["groundwater_level"]])
    
context = pd.concat([train.groupby("Station Code", group_keys=False).tail(checkpoint["sequence_length"]), validation], ignore_index=True)
X, y = create_sequences(context.sort_values(["Station Code", "Month"]), checkpoint["sequence_length"], validation_start)


model = GroundwaterLSTM(len(FEATURE_COLUMNS), checkpoint.get("hidden_size", 128), checkpoint.get("num_layers", 2), checkpoint.get("dropout", 0.2)).to(device)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

with torch.no_grad():
    predicted_scaled = model(torch.tensor(X, dtype=torch.float32).to(device)).cpu().numpy()
    
actual = target_scaler.inverse_transform(y.reshape(-1, 1)).ravel()
predicted = target_scaler.inverse_transform(predicted_scaled.reshape(-1, 1)).ravel()
persistence = target_scaler.inverse_transform(X[:, -1, 2].reshape(-1, 1)).ravel()

def metrics(values):
    return {"mae_m": float(mean_absolute_error(actual, values)), "rmse_m": float(np.sqrt(mean_squared_error(actual, values))), "r2": float(r2_score(actual, values))}

report = {"checkpoint_sha256": checkpoint_hash, "validation_start": str(pd.Timestamp(validation_start).date()), "samples": int(len(actual)), "lstm": metrics(predicted), "persistence": metrics(persistence)}

report["lstm_beats_persistence_mae"] = report["lstm"]["mae_m"] < report["persistence"]["mae_m"]
(ROOT / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
