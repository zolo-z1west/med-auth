from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.capture import router as capture_router
from app.routes.dispense import router as dispense_router
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="med-auth-backend")

# Allow everything for now. Lock this down in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(capture_router)
app.include_router(dispense_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Run with: uvicorn app.main:app --reload --port 8000