import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/detections")
async def receive_detection(request: Request):
    body = await request.json()
    logger.info("Detection received: %s", body)
    return {"received": True}
