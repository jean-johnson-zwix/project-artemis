import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from db import SessionLocal, resolve_detection
from layers.context import gather_context
from layers.reasoning import run_reasoning
from models import DetectionRecord
from notifications import send_discord_resolved, send_teams_resolved

logger = logging.getLogger(__name__)

router = APIRouter()


class ResolveRequest(BaseModel):
    resolved_by: str = "operator"
    resolution_notes: str | None = None


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
        run_reasoning(detection, context, db)
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


@router.post("/detections/{detection_id}/resolve")
def resolve_alert(detection_id: str, body: ResolveRequest):
    """
    Mark an open detection as resolved and restore the asset to OPERATING status
    (when no other active detections remain for that asset).
    """
    db = SessionLocal()
    try:
        updated = resolve_detection(db, detection_id, body.resolved_by, body.resolution_notes)
    finally:
        db.close()

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Detection not found or already resolved.",
        )

    logger.info("Detection %s resolved by %s", detection_id, body.resolved_by)

    for send_fn in (send_teams_resolved, send_discord_resolved):
        try:
            send_fn(updated)
        except Exception as exc:
            logger.error("%s failed for resolved detection %s: %s", send_fn.__name__, detection_id, exc)

    return {"resolved": True, "detection_id": detection_id, "resolved_by": body.resolved_by}
