# src/rndforest/app/main.py

import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
from sklearn.datasets import make_blobs
from ..train import train_model_from_csv
from ..inference import predict_classes

app = FastAPI()

def get_dataset_dir():
    return os.environ.get("DATASET", "/tmp/data")

def get_raw_dir():
    return os.path.join(get_dataset_dir(), "raw")

def get_models_dir():
    return os.environ.get("MODELS_PATH", "/tmp/models")

@app.get("/generate-dataset")
def generate_dataset(n_samples: int = 500, n_features: int = 3, centers: int = 4):
    raw_dir = get_raw_dir()
    os.makedirs(raw_dir, exist_ok=True)
    file_name = f"blobs_{n_samples}n_{n_features}f_{centers}c.csv"
    file_path = os.path.join(raw_dir, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='text/csv', filename=file_name)
    X, y = make_blobs(n_samples=n_samples, n_features=n_features, centers=centers, random_state=42)
    cols = [f'x{i+1}' for i in range(n_features)]
    df = pd.DataFrame(X, columns=cols)
    df['class'] = y
    df.to_csv(file_path, index=False)
    return FileResponse(file_path, media_type='text/csv', filename=file_name)

@app.post("/train")
async def train(file: UploadFile = File(...)):
    models_dir = get_models_dir()
    # FastAPI UploadFile gives you a file-like object
    result = train_model_from_csv(file.file, models_dir)
    return result

@app.post("/predict")
async def predict(data: dict):
    models_dir = get_models_dir()
    preds = predict_classes(data["points"], models_dir)
    return JSONResponse({"predictions": preds})
