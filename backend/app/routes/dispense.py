# backend/app/routes/dispense.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from app.services import dispenser
from app.serial_bridge import write_to_serial

router = APIRouter()

class StartPayload(BaseModel):
    meta: dict = {}

@router.post("/start-dispense")
def start_dispense(background_tasks: BackgroundTasks, payload: StartPayload | None = None):
    """
    Called by serial_bridge when Arduino RTC triggers.
    Starts a dispense job and runs facial verification attempts in background.
    """
    job_id = dispenser.new_job(metadata=(payload.meta if payload else {}))
    background_tasks.add_task(dispenser.run_dispense_workflow, job_id)
    return {"job_id": job_id, "status": "started"}

@router.get("/dispense-status/{job_id}")
def dispense_status(job_id: str):
    job = dispenser.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "attempts": job.get("attempts", 0),
        "result": job.get("result"),
    }

@router.post("/dispense-complete/{job_id}")
def dispense_complete(job_id: str):
    """
    Optional: called by Arduino or serial_bridge when dispensing physically completes.
    Marks job as acknowledged.
    """
    job = dispenser.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job["status"] = "acknowledged"
    return {"job_id": job_id, "status": "acknowledged"}
