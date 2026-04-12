POST /ingest/reading
Ingests a sensor reading, runs all detectors, writes detections to DB, and fires Layer 2+3 as a background task.

Request


{
  "sensor_id": "V-101-PRESS",
  "asset_id": "AREA-HP-SEP:V-101",
  "timestamp": "2024-01-15T08:30:00Z",
  "value": 72.4,
  "unit": "bar",
  "quality_flag": "GOOD"
}
quality_flag: GOOD | BAD | INTERPOLATED | OFFLINE | UNCERTAIN

Response


{
  "written": true,
  "detections_fired": [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  ]
}
detections_fired is empty if no thresholds were breached or all were within cooldown.

Errors

404 — sensor_id or asset_id not found in DB
POST /detections
Internal webhook. Called by Layer 1 to hand off a DetectionRecord to Layer 2+3. Returns immediately; processing is async.

Request


{
  "detection_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "detected_at": "2024-01-15T08:30:00Z",
  "detection_type": "SENSOR_ANOMALY",
  "severity": "HIGH",
  "asset_id": "AREA-HP-SEP:V-101",
  "asset_tag": "V-101",
  "asset_name": "HP Separator V-101",
  "area": "AREA-HP-SEP",
  "detection_data": {
    "z_score": 4.2,
    "value": 72.4,
    "mean": 55.1,
    "stddev": 4.1
  }
}
Response


{ "received": true }
POST /detections/{detection_id}/resolve
Marks a detection as resolved, restores asset status to OPERATING (if no other active detections remain), and sends resolution notifications to Teams and Discord.

Request


{
  "resolved_by": "Jane Smith",
  "resolution_notes": "Replaced diaphragm seal on PT-101-PV. Readings back to normal."
}
Both fields are optional (resolved_by defaults to "operator").

Response


{
  "resolved": true,
  "detection_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "resolved_by": "Jane Smith"
}
Errors

404 — detection not found or already resolved
POST /documents/ingest
Inserts or upserts a document and queues PageIndex tree generation as a background task. If the document already exists, its content is updated and indexed_at is reset to force re-indexing.

Request


{
  "doc_id": "RPT-INSPECT-002",
  "asset_id": "AREA-HP-SEP:V-101",
  "doc_type": "INSPECTION_REPORT",
  "title": "V-101 Pressure Vessel Inspection 2025",
  "revision": "Rev B",
  "author": "J. Ahmed",
  "issue_date": "2025-03-01T00:00:00Z",
  "content": "Section 1: Executive Summary\n..."
}
asset_id, revision, author, issue_date are optional.

Response


{
  "doc_id": "RPT-INSPECT-002",
  "status": "indexing"
}
POST /documents/{doc_id}/upload
Upload an actual file (e.g. PDF) for an already-ingested document.
Accepts multipart/form-data with a `file` field.
Saved to local disk as uploads/<doc_id><ext>.

Response


{ "doc_id": "RPT-INSPECT-002", "filename": "RPT-INSPECT-002.pdf", "size_bytes": 204800 }

Errors

404 — document not found

GET /documents/{doc_id}/download
Download a document. Serves the uploaded file (e.g. PDF) if one exists on disk,
otherwise falls back to the ingested text content as a .txt file.

Response — uploaded file exists

File download with original MIME type (e.g. application/pdf)
  Content-Disposition: attachment; filename="RPT-INSPECT-002.pdf"

Response — no uploaded file (text fallback)

File download with headers:
  Content-Type: text/plain; charset=utf-8
  Content-Disposition: attachment; filename="<title>.txt"

Errors

404 — document not found

GET /documents/{doc_id}/status
Poll indexing progress after POST /documents/ingest.

Response — still indexing


{
  "doc_id": "RPT-INSPECT-002",
  "title": "V-101 Pressure Vessel Inspection 2025",
  "indexed_at": null,
  "status": "indexing"
}
Response — ready


{
  "doc_id": "RPT-INSPECT-002",
  "title": "V-101 Pressure Vessel Inspection 2025",
  "indexed_at": "2024-01-15T08:35:22.123Z",
  "status": "ready"
}
Response — not found


{ "error": "not_found" }
POST /simulate/event
Injects synthetic data for a scenario and runs the full detection + reasoning pipeline end-to-end.

Request


{
  "scenario": "corrosion_spike",
  "asset_id": "AREA-HP-SEP:V-101",
  "overrides": {}
}
scenario values and their relevant overrides:

scenario	Valid asset_id	overrides keys
corrosion_spike	Any asset with corrosion baseline (e.g. AREA-HP-SEP:V-101)	temperature_celsius, coating_failure_pct, wall_thickness_mm, remaining_allowance_mm, base_corrosion_rate_mm_per_year
sensor_anomaly	Asset owning sensor V-101-PRESS	sensor_id, baseline_value, stddev, spike_multiplier
transmitter_divergence	Ignored (uses PT-101-PV/PT-102-PV pair)	base_pressure, divergence_pct
inspection_overdue	Same as corrosion	months_ago, temperature_celsius
Sample — corrosion spike with overrides


{
  "scenario": "corrosion_spike",
  "asset_id": "AREA-HP-SEP:V-101",
  "overrides": {
    "temperature_celsius": 140.0,
    "coating_failure_pct": 45.0
  }
}
Sample — transmitter divergence


{
  "scenario": "transmitter_divergence",
  "asset_id": "AREA-HP-SEP:V-101",
  "overrides": {
    "base_pressure": 52.0,
    "divergence_pct": 12.0
  }
}
Response


{
  "detections_fired": [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  ]
}
detections_fired is empty if the scenario didn't cross a detection threshold.

Error response


{
  "error": "Asset not found: INVALID-ID",
  "detections_fired": []
}
GET /health
Response


{ "status": "ok" }
