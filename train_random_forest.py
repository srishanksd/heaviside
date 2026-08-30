import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import joblib
import json
from pathlib import Path

def main():
    # Setup paths
    base_dir = Path(__file__).resolve().parent
    dataset_path = base_dir / "karnataka_master_dataset.csv"
    weights_dir = base_dir / "weights"
    weights_dir.mkdir(exist_ok=True, parents=True)
    
    print("=" * 50)
    print("Loading dataset...")
    df = pd.read_csv(dataset_path)

    # Rename columns from SIHproject convention to SIH convention
    df = df.rename(columns={
        "Groundwater Level": "groundwater_level",
        "Avg Temperature (°C)": "temperature_c",
        "Total Rainfall (mm)": "rainfall_mm",
        "Soil pH": "soil_ph",
        "Clay (%)": "clay_percent",
        "Sand (%)": "sand_percent",
        "Silt (%)": "silt_percent",
        "Organic Carbon (g/kg)": "organic_carbon",
        "Nitrogen (g/kg)": "nitrogen",
    })
    df["Month"] = pd.to_datetime(df["Month"])
    
    print("=" * 50)
    print("Feature Engineering...")
    df = df.sort_values(by=["Station Code", "Month"]).reset_index(drop=True)
    
    df["GWL_lag_1"] = df.groupby("Station Code")["groundwater_level"].shift(1)
    df["GWL_lag_2"] = df.groupby("Station Code")["groundwater_level"].shift(2)
    df["GWL_lag_3"] = df.groupby("Station Code")["groundwater_level"].shift(3)
    
    df["GWL_rolling_mean_3"] = df.groupby("Station Code")["GWL_lag_1"].rolling(3).mean().reset_index(level=0, drop=True)
    df["GWL_rolling_std_3"] = df.groupby("Station Code")["GWL_lag_1"].rolling(3).std().reset_index(level=0, drop=True)
    
    month_number = df["Month"].dt.month
    df["Month_sin"] = np.sin(2 * np.pi * month_number / 12)
    df["Month_cos"] = np.cos(2 * np.pi * month_number / 12)
    
    RF_FEATURE_COLUMNS = [
        "Latitude", "Longitude",
        "temperature_c", "rainfall_mm",
        "soil_ph", "clay_percent", "sand_percent", "silt_percent",
        "organic_carbon", "nitrogen",
        "GWL_lag_1", "GWL_lag_2", "GWL_lag_3",
        "GWL_rolling_mean_3", "GWL_rolling_std_3",
        "Month_sin", "Month_cos"
    ]
    
    print("=" * 50)
    print("Train/Test Split...")
    
    required_cols = RF_FEATURE_COLUMNS + ["groundwater_level"]
    df = df.dropna(subset=required_cols).copy()
    
    train = df[df["Month"] < "2024-01-01"]
    test = df[df["Month"] >= "2024-01-01"]
    
    X_train = train[RF_FEATURE_COLUMNS]
    y_train = train["groundwater_level"]
    X_test = test[RF_FEATURE_COLUMNS]
    y_test = test["groundwater_level"]
    
    print(f"Train samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")
    
    print("=" * 50)
    print("Training Model...")
    model = RandomForestRegressor(
        n_estimators=300, 
        max_depth=20, 
        min_samples_leaf=2, 
        random_state=42, 
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    print("=" * 50)
    print("Evaluation...")
    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(root_mean_squared_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))
    
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R2:   {r2:.4f}")
    
    print("=" * 50)
    print("Feature Importances...")
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for idx in sorted_idx:
        print(f"{RF_FEATURE_COLUMNS[idx]}: {importances[idx]:.4f}")
    
    print("=" * 50)
    print("Anomaly Detection Setup...")
    train_pred = model.predict(X_train)
    train_absolute_error = np.abs(y_train - train_pred)
    train_error_mean = float(np.mean(train_absolute_error))
    train_error_std = float(np.std(train_absolute_error))
    anomaly_threshold = train_error_mean + 3 * train_error_std
    
    print(f"Train Error Mean: {train_error_mean:.4f}")
    print(f"Train Error Std:  {train_error_std:.4f}")
    print(f"Anomaly Threshold: {anomaly_threshold:.4f}")
    
    print("=" * 50)
    print("Saving Diagnostic Graphs...")
    graphs_dir = base_dir / "graphs" / "rf"
    graphs_dir.mkdir(exist_ok=True, parents=True)

    # 1. Actual vs Predicted
    plt.figure(figsize=(12, 7))
    plt.scatter(y_test, y_pred, alpha=0.5)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
    plt.title("Actual vs Predicted Groundwater Level")
    plt.xlabel("Actual")
    plt.ylabel("Predicted")
    textstr = f'MAE: {mae:.4f}\nRMSE: {rmse:.4f}\nR²: {r2:.4f}'
    props = dict(boxstyle='round', facecolor='white', alpha=0.8)
    plt.gca().text(0.05, 0.95, textstr, transform=plt.gca().transAxes, fontsize=12,
                   verticalalignment='top', bbox=props)
    plt.tight_layout()
    plt.savefig(graphs_dir / "rf_actual_vs_predicted.png", dpi=150)
    plt.close()
    print("Saved rf_actual_vs_predicted.png")

    # 2. Error Distribution
    plt.figure(figsize=(12, 7))
    errors = y_test - y_pred
    plt.hist(errors, bins=50, alpha=0.7, color='blue', edgecolor='black')
    plt.axvline(errors.mean(), color='red', linestyle='dashed', linewidth=2)
    plt.title("Prediction Error Distribution")
    plt.xlabel("Prediction Error (Actual - Predicted)")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(graphs_dir / "rf_error_distribution.png", dpi=150)
    plt.close()
    print("Saved rf_error_distribution.png")

    # 3. Feature Importance
    plt.figure(figsize=(12, 7))
    features = [RF_FEATURE_COLUMNS[i] for i in sorted_idx]
    importances_sorted = importances[sorted_idx]
    plt.barh(features[::-1], importances_sorted[::-1], color='skyblue')
    plt.title("Random Forest Feature Importance")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig(graphs_dir / "rf_feature_importance.png", dpi=150)
    plt.close()
    print("Saved rf_feature_importance.png")

    # 4. Prediction Error & Anomaly Threshold
    plt.figure(figsize=(12, 7))
    test_errors = np.abs(y_test - y_pred)
    plt.plot(range(len(test_errors)), test_errors, alpha=0.7, label='Absolute Error')
    plt.axhline(anomaly_threshold, color='red', linestyle='dashed', linewidth=2, label='Anomaly Threshold')
    plt.title("Prediction Error & Anomaly Threshold")
    plt.xlabel("Test Sample Index")
    plt.ylabel("Absolute Prediction Error")
    plt.legend()
    plt.tight_layout()
    plt.savefig(graphs_dir / "rf_prediction_error.png", dpi=150)
    plt.close()
    print("Saved rf_prediction_error.png")

    print("=" * 50)
    print("Saving...")
    save_dict = {
        'model': model,
        'feature_columns': RF_FEATURE_COLUMNS,
        'anomaly_threshold': anomaly_threshold,
        'train_error_mean': train_error_mean,
        'train_error_std': train_error_std,
        'metrics': {'mae': mae, 'rmse': rmse, 'r2': r2},
    }
    
    model_path = weights_dir / "groundwater_rf.pkl"
    joblib.dump(save_dict, model_path)
    print(f"Model saved to {model_path}")
    
    report = {
        'model_type': 'RandomForestRegressor',
        'n_estimators': 300,
        'max_depth': 20,
        'train_samples': len(train),
        'test_samples': len(test),
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'anomaly_threshold': anomaly_threshold,
        'feature_columns': RF_FEATURE_COLUMNS,
    }
    
    report_path = base_dir / "rf_validation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
    print(f"Validation report saved to {report_path}")

if __name__ == '__main__':
    main()
