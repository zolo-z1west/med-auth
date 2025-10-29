# backend/app/services/dispenser.py
import time
import uuid
import threading
import requests

FACIAL_SERVICE_URL = "http://127.0.0.1:8001/capture"  # facial-rec service
MAX_ATTEMPTS = 15
ATTEMPT_DELAY = 1.5  # seconds between attempts

_lock = threading.Lock()
_jobs = {}  # job_id -> {status, result, attempts, created_at}

def new_job(metadata=None):
    job_id = str(uuid.uuid4())
    job = {"status": "pending", "result": None, "attempts": 0, "meta": metadata, "created_at": time.time()}
    with _lock:
        _jobs[job_id] = job
    return job_id

def get_job(job_id):
    with _lock:
        return _jobs.get(job_id)

def _call_facial_service():
    try:
        r = requests.post(FACIAL_SERVICE_URL, timeout=5)  # adjust if GET or different payload required
        r.raise_for_status()
        data = r.json()
        # Expect facial service to return {"verified": True/False} or similar
        return data.get("verified", False)
    except requests.RequestException:
        return False

def run_dispense_workflow(job_id):
    """
    Blocking work: attempt up to MAX_ATTEMPTS facial checks then set job result.
    Caller may spawn this in a background thread.
    """
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        verified = _call_facial_service()
        with _lock:
            job["attempts"] = attempt
        if verified:
            with _lock:
                job["status"] = "finished"
                job["result"] = {"dispense": True, "reason": "face_verified", "attempts": attempt}
            return
        time.sleep(ATTEMPT_DELAY)

    with _lock:
        job["status"] = "finished"
        job["result"] = {"dispense": False, "reason": "max_attempts_reached", "attempts": MAX_ATTEMPTS}
