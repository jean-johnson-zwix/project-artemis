-- Add PageIndex tree columns to documents
ALTER TABLE "documents"
  ADD COLUMN IF NOT EXISTS "page_index_tree" jsonb,
  ADD COLUMN IF NOT EXISTS "indexed_at"      timestamptz;

CREATE INDEX IF NOT EXISTS "documents_indexed_at_idx" ON "documents" ("indexed_at");

-- Wiki index table: one row per document, updated automatically after tree generation
CREATE TABLE IF NOT EXISTS "wiki_index" (
  "doc_id"          text        NOT NULL,
  "doc_type"        text        NOT NULL,
  "title"           text        NOT NULL,
  "one_line_summary" text       NOT NULL,
  "updated_at"      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT "wiki_index_pkey" PRIMARY KEY ("doc_id"),
  CONSTRAINT "wiki_index_doc_id_fkey" FOREIGN KEY ("doc_id") REFERENCES "documents" ("doc_id") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "wiki_index_doc_type_idx" ON "wiki_index" ("doc_type");
