from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "central_logs.json")


class LogModel(BaseModel):
    service_name: str
    level: str
    message: str
    timestamp: datetime


@app.post("/log")
async def receive_log(log: LogModel):

    log_entry = log.model_dump()

    # Convert datetime to ISO string
    log_entry["timestamp"] = log_entry["timestamp"].isoformat()

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    return {"status": "stored"}