-- This migration was generated against a local database that already had
-- wiki_index, so it only contains a constraint change with no CREATE TABLE.
-- The table is created by the next migration (20260412200000_add_pageindex_and_wiki).
-- On fresh databases this is a no-op; on existing databases it updates the FK.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'wiki_index') THEN
    ALTER TABLE "wiki_index" DROP CONSTRAINT IF EXISTS "wiki_index_doc_id_fkey";
    ALTER TABLE "wiki_index" ADD CONSTRAINT "wiki_index_doc_id_fkey"
      FOREIGN KEY ("doc_id") REFERENCES "documents"("doc_id")
      ON DELETE RESTRICT ON UPDATE CASCADE;
  END IF;
END
$$;
