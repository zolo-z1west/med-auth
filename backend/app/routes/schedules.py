from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4
from pathlib import Path
import json
from datetime import datetime, date, time as dtime, timedelta

router = APIRouter()
DATA_FILE = Path("data/schedules.json")
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
if not DATA_FILE.exists():
    DATA_FILE.write_text("[]")

class ScheduleIn(BaseModel):
    patient_id: str
    dispense_time: str = Field(..., description="ISO datetime or HH:MM")
    amount: int = 1
    timezone: Optional[str] = None

class ScheduleOut(ScheduleIn):
    id: str

def _load() -> List[dict]:
    return json.loads(DATA_FILE.read_text())

def _save(data: List[dict]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2))

def _parse_dispense_time(s: str) -> datetime:
    # try ISO first
    try:
        return datetime.fromisoformat(s)
    except Exception:
        hh, mm = s.split(":")
        today = date.today()
        return datetime.combine(today, dtime(int(hh), int(mm)))

@router.post("/schedules", response_model=ScheduleOut)
def create_schedule(inp: ScheduleIn):
    data = _load()
    obj = inp.dict()
    obj["id"] = str(uuid4())
    dt = _parse_dispense_time(obj["dispense_time"])
    obj["_next_dt"] = dt.isoformat()
    data.append(obj)
    _save(data)
    return obj

@router.get("/schedules", response_model=List[ScheduleOut])
def list_schedules():
    data = _load()
    for item in data:
        if "_next_dt" not in item:
            try:
                item["_next_dt"] = _parse_dispense_time(item["dispense_time"]).isoformat()
            except Exception:
                item["_next_dt"] = ""
    return data

@router.get("/next-schedule")
def next_schedule():
    data = _load()
    now = datetime.now()
    candidates = []
    for item in data:
        try:
            dt = datetime.fromisoformat(item.get("_next_dt") or _parse_dispense_time(item["dispense_time"]).isoformat())
        except Exception:
            continue
        # if time is earlier than now, consider next-day occurrence (simple daily schedule assumption)
        if dt < now:
            dt = dt + timedelta(days=1)
        candidates.append((dt, item))
    if not candidates:
        return {"next": None}
    candidates.sort(key=lambda x: x[0])
    dt, item = candidates[0]
    return {"next": {
        "id": item["id"],
        "patient_id": item["patient_id"],
        "dispense_time": item["dispense_time"],
        "amount": item["amount"],
        "when_iso": dt.isoformat()
    } }

@router.delete("/schedules/{sched_id}")
def delete_schedule(sched_id: str):
    data = _load()
    new = [d for d in data if d.get("id") != sched_id]
    if len(new) == len(data):
        raise HTTPException(status_code=404, detail="not found")
    _save(new)
    return {"deleted": sched_id}
