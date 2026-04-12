-- DropForeignKey
ALTER TABLE "wiki_index" DROP CONSTRAINT "wiki_index_doc_id_fkey";

-- AddForeignKey
ALTER TABLE "wiki_index" ADD CONSTRAINT "wiki_index_doc_id_fkey" FOREIGN KEY ("doc_id") REFERENCES "documents"("doc_id") ON DELETE RESTRICT ON UPDATE CASCADE;
