from fastapi import FastAPI, UploadFile, File
from swara.inference import predict_file  # you’ll add this later

app = FastAPI(title="Swara API")

@app.get("/healthz")
def health():
    return {"status": "ok"}

@app.post("/classify")
async def classify_audio(file: UploadFile = File(...)):
    path = f"/tmp/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    cluster = predict_file(path)          # returns your cluster label
    return {"cluster": int(cluster)}
