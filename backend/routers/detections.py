import logging

from fastapi import APIRouter, BackgroundTasks, Request

from db import SessionLocal
from layers.context import gather_context
from models import DetectionRecord

logger = logging.getLogger(__name__)

router = APIRouter()


def _process_detection(detection: DetectionRecord) -> None:
    """
    Background task: runs Layer 2 (context) then hands off to Layer 3.
    Opens its own DB session — the request session is already closed by this point.
    """
    db = SessionLocal()
    try:
        context = gather_context(detection, db)
        logger.info(
            "Layer 2 complete for detection %s — %d trend rows, %d docs",
            detection.detection_id,
            len(context.sensor_trend),
            len(context.relevant_docs),
        )
        # Layer 3 wired here next:
        # from layers.reasoning import run_reasoning
        # run_reasoning(detection, context, db)
    except Exception as exc:
        logger.error("Layer 2 failed for detection %s: %s", detection.detection_id, exc, exc_info=True)
    finally:
        db.close()


@router.post("/detections")
async def receive_detection(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook called by Layer 1 after each confirmed detection.
    Parses the DetectionRecord, returns 200 immediately, and processes async.
    """
    body = await request.json()
    try:
        detection = DetectionRecord(**body)
    except Exception as exc:
        logger.warning("Could not parse detection body: %s — body: %s", exc, body)
        return {"received": True, "error": "parse_failed"}

    background_tasks.add_task(_process_detection, detection)
    return {"received": True}
