-- Track the Discord thread created for each detection alert
ALTER TABLE "detections"
  ADD COLUMN IF NOT EXISTS "discord_thread_id" TEXT;

CREATE INDEX IF NOT EXISTS "detections_discord_thread_id_idx" ON "detections" ("discord_thread_id");
