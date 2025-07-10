import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler

def get_model_path(models_dir):
    return os.path.join(models_dir, "rf_model.joblib")

def get_scaler_path(models_dir):
    return os.path.join(models_dir, "rf_scaler.joblib")

def train_model_from_csv(csv_file, models_dir):
    df = pd.read_csv(csv_file)
    feature_cols = [col for col in df.columns if col.startswith('x')]
    X = df[feature_cols].values
    y = df['class'].values
    scaler = MinMaxScaler()
    X_norm = scaler.fit_transform(X)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_norm, y)
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(model, get_model_path(models_dir))
    joblib.dump(scaler, get_scaler_path(models_dir))
    return {"status": "trained", "samples": len(X), "features": feature_cols}
