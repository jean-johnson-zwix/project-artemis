import { NextRequest } from 'next/server'
import { streamText } from 'ai'
import { openai } from '@/lib/ai'
import prisma from '@/lib/prisma'

export const runtime = 'nodejs'

export async function POST(request: NextRequest) {
  const { messages } = await request.json()

  const lastUserMessage = messages.findLast((m: { role: string }) => m.role === 'user')?.content ?? ''

  let context = ''
  let sources: Array<{ id: string; title: string; docType: string }> = []

  if (!process.env.OPENAI_API_KEY || process.env.OPENAI_API_KEY === 'your-key-here') {
    const stream = new ReadableStream({
      start(controller) {
        const msg = 'OpenAI API key is not configured. Please set OPENAI_API_KEY in your .env file to use the knowledge assistant.'
        // Emit in AI SDK text stream format
        controller.enqueue(new TextEncoder().encode(`0:${JSON.stringify(msg)}\n`))
        controller.close()
      },
    })
    return new Response(stream, {
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    })
  }

  try {
    // Try vector search first
    const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'text-embedding-3-small',
        input: lastUserMessage,
      }),
    })

    if (embeddingResponse.ok) {
      const embeddingData = await embeddingResponse.json()
      const embedding = embeddingData.data[0].embedding
      const embeddingStr = `[${embedding.join(',')}]`

      const docs = await prisma.$queryRawUnsafe<Array<{ id: string; title: string; content: string; doc_type: string }>>(
        `SELECT id, title, content, doc_type FROM documents WHERE embedding IS NOT NULL ORDER BY embedding <=> $1::vector LIMIT 5`,
        embeddingStr
      )

      sources = docs.map((d) => ({ id: d.id, title: d.title, docType: d.doc_type }))
      context = docs.map((d) => `[${d.title}]\n${d.content}`).join('\n\n---\n\n')
    }
  } catch {
    // Fall back to keyword search
    const keywords = lastUserMessage.split(' ').filter((w: string) => w.length > 3).slice(0, 5)
    if (keywords.length > 0) {
      const docs = await prisma.document.findMany({
        where: {
          OR: keywords.map((kw: string) => ({
            content: { contains: kw, mode: 'insensitive' as const },
          })),
        },
        take: 5,
      })
      sources = docs.map((d) => ({ id: d.id, title: d.title, docType: d.docType }))
      context = docs.map((d) => `[${d.title}]\n${d.content}`).join('\n\n---\n\n')
    }
  }

  const systemPrompt = `You are an industrial AI assistant for Hackazona, an oil & gas facility management platform.
You help engineers and operators with technical questions about equipment, procedures, maintenance, and safety.

${context ? `RELEVANT DOCUMENTS:\n\n${context}\n\nUse the above documents to answer the user's question accurately.` : 'No specific documents found for this query. Answer based on general industrial knowledge.'}

${sources.length > 0 ? `\n\nAt the end of your response, include:\n\nSources:\n${sources.map((s) => `- ${s.title} (${s.docType})`).join('\n')}` : ''}

Always be precise, safety-conscious, and cite relevant procedures when applicable.`

  const result = streamText({
    model: openai('gpt-4o-mini'),
    system: systemPrompt,
    messages: messages.map((m: { role: string; content: string }) => ({
      role: m.role as 'user' | 'assistant' | 'system',
      content: m.content,
    })),
  })

  // Return as simple text stream that our client can parse
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder()
      for await (const chunk of result.textStream) {
        controller.enqueue(encoder.encode(`0:${JSON.stringify(chunk)}\n`))
      }
      controller.close()
    },
  })

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
