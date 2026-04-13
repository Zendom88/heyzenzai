from fastapi import APIRouter
from datetime import datetime
from zoneinfo import ZoneInfo

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "heyzenzai-backend",
        "time": datetime.now(ZoneInfo("Asia/Singapore")).isoformat(),
    }
