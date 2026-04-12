"""
Document ingestion endpoint.

POST /documents/ingest
  Accepts a new document (metadata + raw text), writes it to the documents table,
  and schedules PageIndex tree generation as a background task.
  Returns 200 immediately — indexing is async.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import text

from db import SessionLocal
from layers.indexing import build_page_index
from models import DocumentIngestRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents")


def _run_build_page_index(doc_id: str) -> None:
    """Background task wrapper — opens its own DB session."""
    db = SessionLocal()
    try:
        build_page_index(doc_id, db)
    except Exception as exc:
        logger.error("Background PageIndex build failed for %s: %s", doc_id, exc, exc_info=True)
    finally:
        db.close()


@router.post("/ingest")
async def ingest_document(body: DocumentIngestRequest, background_tasks: BackgroundTasks):
    """
    Ingest a new document and schedule PageIndex tree generation.

    The tree is built asynchronously — the document is immediately queryable
    via keyword fallback, and via PageIndex once indexed_at is set.
    Poll GET /documents/{doc_id}/status to check indexing progress.
    """
    db = SessionLocal()
    try:
        db.execute(
            text(
                "INSERT INTO documents "
                "(doc_id, asset_id, doc_type, title, revision, author, issue_date, content) "
                "VALUES (:did, :aid, :dtype, :title, :rev, :author, :idate, :content) "
                "ON CONFLICT (doc_id) DO UPDATE "
                "SET content = EXCLUDED.content, "
                "    doc_type = EXCLUDED.doc_type, "
                "    title = EXCLUDED.title, "
                "    indexed_at = NULL"  # force re-indexing on content update
            ),
            {
                "did": body.doc_id,
                "aid": body.asset_id,
                "dtype": body.doc_type,
                "title": body.title,
                "rev": body.revision,
                "author": body.author,
                "idate": body.issue_date,
                "content": body.content,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed to insert document %s: %s", body.doc_id, exc)
        raise
    finally:
        db.close()

    background_tasks.add_task(_run_build_page_index, body.doc_id)
    logger.info("Document %s ingested — PageIndex build queued", body.doc_id)

    return {"doc_id": body.doc_id, "status": "indexing"}


@router.get("/{doc_id}/status")
async def document_status(doc_id: str):
    """
    Returns the indexing status of a document.
    indexed_at: null means still processing; set means tree is ready.
    """
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT doc_id, title, indexed_at FROM documents WHERE doc_id = :did"),
            {"did": doc_id},
        ).fetchone()
    finally:
        db.close()

    if not row:
        return {"error": "not_found"}

    return {
        "doc_id": row[0],
        "title": row[1],
        "indexed_at": row[2].isoformat() if row[2] else None,
        "status": "ready" if row[2] else "indexing",
    }
