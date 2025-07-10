# src/rndforest/app/main.py

import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
from sklearn.datasets import make_blobs
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
import joblib

app = FastAPI()

# Paths
def get_dataset_dir():
    return os.environ.get("DATASET", "/tmp/data")

def get_raw_dir():
    return os.path.join(get_dataset_dir(), "raw")

def get_models_dir():
    return os.environ.get("MODELS_PATH", "/tmp/models")

def get_model_path():
    return os.path.join(get_models_dir(), "rf_model.joblib")

def get_scaler_path():
    return os.path.join(get_models_dir(), "rf_scaler.joblib")

# Endpoint: Generate (and cache) raw, unnormalized data
@app.get("/generate-dataset")
def generate_dataset(n_samples: int = 500, n_features: int = 3, centers: int = 4):
    raw_dir = get_raw_dir()
    os.makedirs(raw_dir, exist_ok=True)
    file_name = f"blobs_{n_samples}n_{n_features}f_{centers}c.csv"
    file_path = os.path.join(raw_dir, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='text/csv', filename=file_name)
    # Generate RAW (unnormalized) dataset for Houdini plotting
    X, y = make_blobs(n_samples=n_samples, n_features=n_features, centers=centers, random_state=42)
    cols = [f'x{i+1}' for i in range(n_features)]
    df = pd.DataFrame(X, columns=cols)
    df['class'] = y
    df.to_csv(file_path, index=False)
    return FileResponse(file_path, media_type='text/csv', filename=file_name)

# Endpoint: Train model (normalization done here)
@app.post("/train")
async def train(file: UploadFile = File(...)):
    os.makedirs(os.path.join(get_dataset_dir(), "processed"), exist_ok=True)
    df = pd.read_csv(file.file)
    # Support arbitrary n_features (x1, x2, x3, ...)
    feature_cols = [col for col in df.columns if col.startswith('x')]
    X = df[feature_cols].values
    y = df['class'].values
    scaler = MinMaxScaler()
    X_norm = scaler.fit_transform(X)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_norm, y)
    # Save model and scaler
    joblib.dump(model, get_model_path())
    joblib.dump(scaler, get_scaler_path())
    return {"status": "trained", "samples": len(X), "features": feature_cols}

# Endpoint: Predict class for incoming points (normalization behind scenes)
@app.post("/predict")
async def predict(data: dict):
    # Data format: { "points": [[x1, x2, x3], ...] }
    model = joblib.load(get_model_path())
    scaler = joblib.load(get_scaler_path())
    X_new = pd.DataFrame(data["points"]).values
    X_norm = scaler.transform(X_new)
    preds = model.predict(X_norm)
    return JSONResponse({"predictions": preds.tolist()})

# (Optional) Normalize points using saved scaler (for debugging)
@app.post("/normalize")
async def normalize(data: dict):
    scaler = joblib.load(get_scaler_path())
    X = pd.DataFrame(data["points"]).values
    X_norm = scaler.transform(X)
    return JSONResponse({"normalized": X_norm.tolist()})

# (Optional) Denormalize points using saved scaler (for debugging)
@app.post("/denormalize")
async def denormalize(data: dict):
    scaler = joblib.load(get_scaler_path())
    X = pd.DataFrame(data["points"]).values
    X_denorm = scaler.inverse_transform(X)
    return JSONResponse({"denormalized": X_denorm.tolist()})
