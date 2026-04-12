import { NextRequest, NextResponse } from 'next/server'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  const body = await request.json()

  const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000'

  const res = await fetch(`${backendUrl}/detections/${id}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
