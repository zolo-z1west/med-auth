from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
import time

router = APIRouter()

# simple in-memory store. Replace with DB for production.
_dispense_store: Dict[str, dict] = {}

class DispenseRequest(BaseModel):
    patient_id: str
    amount: int

class DispenseStatus(BaseModel):
    patient_id: str
    status: str
    timestamp: float

@router.post("/start-dispense")
async def start_dispense(req: DispenseRequest):
    # create a job id from timestamp
    job_id = f"job-{int(time.time()*1000)}"
    _dispense_store[job_id] = {"patient_id": req.patient_id, "amount": req.amount, "status": "pending", "ts": time.time()}
    return {"job_id": job_id}

@router.get("/dispense-status/{job_id}")
async def dispense_status(job_id: str):
    job = _dispense_store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {"job_id": job_id, "status": job["status"], "patient_id": job["patient_id"]}

# For testing: mark job complete
@router.post("/dispense-complete/{job_id}")
async def dispense_complete(job_id: str):
    job = _dispense_store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    job["status"] = "completed"
    return {"job_id": job_id, "status": "completed"}