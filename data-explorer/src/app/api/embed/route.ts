import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function POST() {
  if (!process.env.OPENAI_API_KEY || process.env.OPENAI_API_KEY === 'your-key-here') {
    return NextResponse.json({ error: 'OPENAI_API_KEY not configured' }, { status: 400 })
  }

  const docs = await prisma.document.findMany({
    where: {},
    select: { id: true, title: true, content: true },
  })

  // Filter to docs without embeddings
  const docsWithoutEmbeddings = await prisma.$queryRaw<Array<{ id: string }>>`
    SELECT id FROM documents WHERE embedding IS NULL
  `
  const idsWithoutEmbeddings = new Set(docsWithoutEmbeddings.map((d) => d.id))
  const toEmbed = docs.filter((d) => idsWithoutEmbeddings.has(d.id))

  let processed = 0
  for (const doc of toEmbed) {
    const text = `${doc.title}\n\n${doc.content}`.slice(0, 8000)

    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'text-embedding-3-small',
        input: text,
      }),
    })

    if (!response.ok) continue

    const data = await response.json()
    const embedding = data.data[0].embedding
    const embeddingStr = `[${embedding.join(',')}]`

    await prisma.$executeRawUnsafe(
      `UPDATE documents SET embedding = $1::vector WHERE id = $2`,
      embeddingStr,
      doc.id
    )

    processed++
  }

  // Create IVFFlat index if we processed documents
  if (processed > 0) {
    try {
      await prisma.$executeRaw`
        CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)
      `
    } catch {
      // Index may already exist or not enough vectors yet
    }
  }

  return NextResponse.json({ processed, total: docs.length })
}
