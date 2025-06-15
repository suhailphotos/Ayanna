echo $HF_TOKEN
uvicorn imgseg.app.main:app --host 0.0.0.0 --port 8000
clear
exit
