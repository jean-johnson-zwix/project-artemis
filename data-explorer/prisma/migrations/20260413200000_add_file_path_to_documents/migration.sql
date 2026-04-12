-- Add optional file_path to documents for local file download support
ALTER TABLE "documents"
  ADD COLUMN IF NOT EXISTS "file_path" TEXT;
