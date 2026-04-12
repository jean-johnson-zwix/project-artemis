"""
Layer: Document Indexing

Builds and maintains the PageIndex tree and wiki index for every document.
Called at startup (seed existing docs) and on every POST /documents/ingest.

Two public entry points:
  build_page_index(doc_id, db)   — generates tree, writes to documents, refreshes wiki index
  seed_unindexed_documents(db)   — queues build_page_index for all docs with indexed_at IS NULL
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import instructor
from openai import AzureOpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from models import PageIndexNode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Few-shot example embedded in the tree-builder system prompt.
# Kept here (not in a separate file) so the prompt is always self-contained.
# ---------------------------------------------------------------------------

_TREE_BUILDER_EXAMPLE = """
{
  "title": "HP Separator Inspection Report 2024",
  "node_id": "root",
  "start_index": 0,
  "end_index": 8420,
  "summary": "Annual wall thickness and coating inspection of HP Separator V-101 in AREA-HP-SEP. Assets: V-101. Covers measurement methodology, thickness readings, coating holiday survey, corrosion rate analysis, and recommendations.",
  "nodes": [
    {
      "title": "Executive Summary",
      "node_id": "0001",
      "start_index": 0,
      "end_index": 620,
      "summary": "V-101 minimum wall thickness recorded at 4.7 mm, below design minimum of 5.0 mm. Corrosion rate elevated at 0.38 mm/year. Immediate re-inspection within 6 months recommended. Assets: V-101.",
      "nodes": []
    },
    {
      "title": "Wall Thickness Measurements",
      "node_id": "0002",
      "start_index": 621,
      "end_index": 2540,
      "summary": "Ultrasonic thickness measurements across 24 survey points on V-101 shell. Minimum recorded: 4.7 mm at grid E-3. Design minimum: 5.0 mm. Remaining corrosion allowance: 0.7 mm. Assets: V-101.",
      "nodes": [
        {
          "title": "Shell Course Measurements",
          "node_id": "0003",
          "start_index": 621,
          "end_index": 1820,
          "summary": "24-point grid scan of V-101 shell courses 1 and 2. Min: 4.7 mm (E-3), Max: 5.9 mm (A-1). Assets: V-101.",
          "nodes": []
        }
      ]
    }
  ]
}
"""

_TREE_BUILDER_SYSTEM = f"""You are a document structure analyst for industrial maintenance records.
Your task: given raw text from a technical document, produce a hierarchical PageIndex tree as JSON.

Rules (non-negotiable):
1. Use character offsets (start_index, end_index) into the raw text — NOT page numbers.
2. Every node summary MUST list all asset tags mentioned in that section (e.g. V-101, PT-101-PV, AREA-HP-SEP).
   If a section contains no asset tags, write "No specific asset tags."
3. node_id values: root for the top node, then 0001, 0002, etc. in document order.
4. The root node spans the entire document (start_index: 0, end_index: <len of text>).
5. Aim for 2–4 levels of hierarchy following the document's natural section structure.
6. Keep summaries factual and grounded in the document text — no inference.

Output format (JSON only, no markdown fences):

Example output:
{_TREE_BUILDER_EXAMPLE}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_page_index(doc_id: str, db: Session) -> None:
    """
    Generate a PageIndex tree for the given document, write it to the DB,
    then update the wiki index row.

    Safe to call multiple times — will overwrite an existing tree.
    """
    row = db.execute(
        text("SELECT title, doc_type, content FROM documents WHERE doc_id = :did"),
        {"did": doc_id},
    ).fetchone()

    if not row:
        logger.error("build_page_index: doc_id %s not found", doc_id)
        return

    title, doc_type, content = row

    try:
        tree = _call_tree_builder(content, title)
    except Exception as exc:
        logger.error("PageIndex tree generation failed for %s: %s", doc_id, exc, exc_info=True)
        return

    tree_json = tree.model_dump_json()
    now = datetime.now(timezone.utc)

    db.execute(
        text(
            "UPDATE documents "
            "SET page_index_tree = CAST(:tree AS jsonb), indexed_at = :now "
            "WHERE doc_id = :did"
        ),
        {"tree": tree_json, "now": now, "did": doc_id},
    )
    db.commit()
    logger.info("PageIndex tree written for %s (%s)", doc_id, title)

    _refresh_wiki_index(doc_id, doc_type, title, tree, db)


def seed_unindexed_documents(db: Session) -> list[str]:
    """
    Find all documents that have not yet been indexed (indexed_at IS NULL)
    and trigger build_page_index for each.

    Returns the list of doc_ids queued.
    Called once at application startup.
    """
    rows = db.execute(
        text("SELECT doc_id FROM documents WHERE indexed_at IS NULL ORDER BY doc_id")
    ).fetchall()

    doc_ids = [r[0] for r in rows]

    if not doc_ids:
        logger.info("seed_unindexed_documents: all documents already indexed")
        return []

    logger.info("seed_unindexed_documents: indexing %d document(s): %s", len(doc_ids), doc_ids)
    for doc_id in doc_ids:
        try:
            build_page_index(doc_id, db)
        except Exception as exc:
            logger.error("Failed to index %s: %s", doc_id, exc)

    return doc_ids


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_instructor_client() -> instructor.Instructor:
    """Build an instructor-wrapped Azure OpenAI client with JSON mode enforcement."""
    raw = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def _call_tree_builder(content: str, title: str) -> PageIndexNode:
    """
    Call Azure OpenAI (via instructor) to generate a validated PageIndexNode tree.
    instructor retries automatically on schema mismatch — up to 3 attempts.
    """
    client = _get_instructor_client()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    user_message = (
        f"Document title: {title}\n\n"
        f"Document text (character length: {len(content)}):\n\n"
        f"{content}"
    )

    tree: PageIndexNode = client.chat.completions.create(
        model=deployment,
        response_model=PageIndexNode,
        messages=[
            {"role": "system", "content": _TREE_BUILDER_SYSTEM},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=4000,
        max_retries=3,
    )

    return tree


def _refresh_wiki_index(
    doc_id: str,
    doc_type: str,
    title: str,
    tree: PageIndexNode,
    db: Session,
) -> None:
    """
    Upsert a wiki_index row from the root node's summary.
    The root summary is the one-line entry the Step 2 selector reads.
    It must already contain asset tags (enforced by tree builder prompt).
    """
    # Root summary is the canonical one-line description for the wiki index.
    # Truncate to 500 chars to keep the wiki index compact for LLM consumption.
    one_line = tree.summary[:500].replace("\n", " ").strip()

    db.execute(
        text(
            "INSERT INTO wiki_index (doc_id, doc_type, title, one_line_summary, updated_at) "
            "VALUES (:did, :dtype, :title, :summary, :now) "
            "ON CONFLICT (doc_id) DO UPDATE "
            "SET doc_type = EXCLUDED.doc_type, "
            "    title = EXCLUDED.title, "
            "    one_line_summary = EXCLUDED.one_line_summary, "
            "    updated_at = EXCLUDED.updated_at"
        ),
        {
            "did": doc_id,
            "dtype": doc_type,
            "title": title,
            "summary": one_line,
            "now": datetime.now(timezone.utc),
        },
    )
    db.commit()
    logger.info("wiki_index upserted for %s", doc_id)
