import { PrismaClient } from '@prisma/client'
import * as dotenv from 'dotenv'
import * as fs from 'fs'
import * as path from 'path'

dotenv.config()

const prisma = new PrismaClient()

async function main() {
  const rows = await prisma.$queryRaw<Array<{ doc_id: string; embedding: string }>>`
    SELECT doc_id, embedding::text FROM documents WHERE embedding IS NOT NULL
  `

  const out = Object.fromEntries(rows.map((r) => [r.doc_id, r.embedding]))
  const outPath = path.join(__dirname, '../prisma/seeds/documentEmbeddings.json')
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2))
  console.log(`Wrote ${rows.length} embeddings to ${outPath}`)

  await prisma.$disconnect()
}

main().catch((e) => { console.error(e); process.exit(1) })
