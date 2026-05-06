from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict

app = FastAPI(title="Scholarship Search Agent API")


class ProfileRequest(BaseModel):
    profile: Dict[str, Any]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Scholarship Search Agent API"
    }


@app.get("/demo/latest")
def get_latest_demo():
    return {
        "message": "Later this endpoint will return the latest demo JSON output."
    }


@app.post("/search")
def search_scholarships(request: ProfileRequest):
    return {
        "message": "Later this endpoint will run the scholarship agent.",
        "received_profile": request.profile
    }