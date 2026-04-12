/**
 * Script to generate embeddings for all documents using Azure OpenAI.
 * Run with: npx tsx scripts/embed-documents.ts
 */

import { PrismaClient } from '@prisma/client'
import * as dotenv from 'dotenv'

dotenv.config()

const AZURE_ENDPOINT = process.env.AZURE_OPENAI_ENDPOINT ?? "https://aiproject21783899.cognitiveservices.azure.com/openai/v1/"
const DEPLOYMENT_NAME = "text-embedding-3-small"
const API_KEY = process.env.AZURE_OPENAI_API_KEY

if (!API_KEY) {
  console.error('AZURE_OPENAI_API_KEY is required in .env')
  process.exit(1)
}

const prisma = new PrismaClient()

async function getEmbedding(text: string): Promise<number[]> {
  const url = `${AZURE_ENDPOINT}embeddings`
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-key': API_KEY,
    },
    body: JSON.stringify({
      model: DEPLOYMENT_NAME,
      input: text,
    }),
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Azure OpenAI error ${response.status}: ${error}`)
  }

  const data = await response.json()
  return data.data[0].embedding as number[]
}

async function main() {
  console.log('Finding documents without embeddings...')

  const docsWithoutEmbeddings = await prisma.$queryRaw<Array<{ doc_id: string; title: string; content: string }>>`
    SELECT doc_id, title, content FROM documents WHERE embedding IS NULL
  `

  console.log(`Found ${docsWithoutEmbeddings.length} documents to embed`)

  let processed = 0
  let failed = 0

  for (const doc of docsWithoutEmbeddings) {
    const text = `${doc.title}\n\n${doc.content}`.slice(0, 8000)

    try {
      const embedding = await getEmbedding(text)
      const embeddingStr = `[${embedding.join(',')}]`

      await prisma.$executeRawUnsafe(
        `UPDATE documents SET embedding = $1::vector WHERE doc_id = $2`,
        embeddingStr,
        doc.doc_id
      )

      processed++
      process.stdout.write(`\rEmbedded ${processed}/${docsWithoutEmbeddings.length} documents`)
    } catch (err) {
      failed++
      console.error(`\nFailed to embed doc ${doc.doc_id} (${doc.title}):`, err)
    }
  }

  console.log(`\n\nDone. Processed: ${processed}, Failed: ${failed}`)

  if (processed > 0) {
    console.log('Creating IVFFlat index...')
    try {
      await prisma.$executeRaw`
        CREATE INDEX IF NOT EXISTS documents_embedding_idx
        ON documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
      `
      console.log('Index created (or already exists).')
    } catch (err) {
      console.warn('Could not create index (may need more vectors, or already exists):', err)
    }
  }

  await prisma.$disconnect()
}

main().catch((err) => {
  console.error(err)
  prisma.$disconnect()
  process.exit(1)
})
