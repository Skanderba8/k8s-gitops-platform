from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
import socket
import os
#v2
app = FastAPI()
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/info")
def info():
    return {
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("APP_ENV", "dev"),
        "hostname": socket.gethostname()
    }

@app.get("/items")
def get_items():
    return [
        {"id": 1, "name": "item-one"},
        {"id": 2, "name": "item-two"},
        {"id": 3, "name": "item-three"}
    ]

@app.post("/items")
def create_item(item: dict):
    return {"id": 4, **item}
