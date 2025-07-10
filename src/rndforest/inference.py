import os
import pandas as pd
import joblib

def get_model_path(models_dir):
    return os.path.join(models_dir, "rf_model.joblib")

def get_scaler_path(models_dir):
    return os.path.join(models_dir, "rf_scaler.joblib")

def predict_classes(points, models_dir):
    model = joblib.load(get_model_path(models_dir))
    scaler = joblib.load(get_scaler_path(models_dir))
    X_new = pd.DataFrame(points).values
    X_norm = scaler.transform(X_new)
    preds = model.predict(X_norm)
    return preds.tolist()
