import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ docId: string }> }
) {
  const { docId } = await params

  const upstream = await fetch(`${BACKEND_URL}/documents/${docId}/download`)

  if (!upstream.ok) {
    return new NextResponse(null, { status: upstream.status })
  }

  const body = await upstream.arrayBuffer()
  const contentType = upstream.headers.get('Content-Type') ?? 'application/octet-stream'
  const disposition = upstream.headers.get('Content-Disposition') ?? `attachment; filename="${docId}.txt"`

  return new NextResponse(body, {
    status: 200,
    headers: {
      'Content-Type': contentType,
      'Content-Disposition': disposition,
    },
  })
}
