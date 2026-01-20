from fastapi import FastAPI, HTTPException
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import os
import json

# ----------------------------
# App setup
# ----------------------------
app = FastAPI()

# ----------------------------
# Firebase setup (ENV BASED)
# ----------------------------
FIREBASE_DB_URL = "https://employee-time-tracker-43b16-default-rtdb.firebaseio.com/"

service_account_info = json.loads(
    os.environ["FIREBASE_SERVICE_ACCOUNT"]
)

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL
    })

print("✅ Firebase initialized successfully")

# ----------------------------
# Interval settings
# ----------------------------
INTERVAL_SECONDS = 5
last_punch_times = {}

# ----------------------------
# POST Attendance
# ----------------------------
@app.post("/attendance")
def receive_attendance(data: dict | list):
    records = [data] if isinstance(data, dict) else data
    responses = []

    for record in records:
        emp_id = record.get("emp_id", "unknown")
        now = datetime.utcnow()

        last_time = last_punch_times.get(emp_id)
        if last_time:
            diff = (now - last_time).total_seconds()
            if diff < INTERVAL_SECONDS:
                responses.append({
                    "emp_id": emp_id,
                    "status": "ignored",
                    "message": f"Punch ignored (<{INTERVAL_SECONDS}s)"
                })
                continue

        record["received_at"] = now.isoformat()

        try:
            ref = db.reference("/attendance")
            ref.push(record)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        last_punch_times[emp_id] = now

        responses.append({
            "emp_id": emp_id,
            "status": "success",
            "data": record
        })

    return responses


# ----------------------------
# GET Attendance
# ----------------------------
@app.get("/attendance")
def get_attendance():
    try:
        ref = db.reference("/attendance")
        return {
            "status": "success",
            "data": ref.get() or {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
