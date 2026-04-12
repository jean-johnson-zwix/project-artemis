-- Capture how an alert was resolved (free-text from the operator)
ALTER TABLE "detections"
  ADD COLUMN IF NOT EXISTS "resolution_notes" TEXT;
