-- Add resolution tracking to detections
-- resolved_at: timestamp when the alert was marked resolved (NULL = still active)
-- resolved_by: free-text name / user identifier of who resolved it
ALTER TABLE "detections"
  ADD COLUMN IF NOT EXISTS "resolved_at"  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS "resolved_by"  TEXT;

CREATE INDEX IF NOT EXISTS "detections_resolved_at_idx" ON "detections" ("resolved_at");
