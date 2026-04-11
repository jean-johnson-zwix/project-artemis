import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sensorId: string }> }
) {
  const { sensorId } = await params
  const { searchParams } = new URL(request.url)
  const from = searchParams.get('from')
  const to = searchParams.get('to')

  const where: Record<string, unknown> = { sensorId }
  if (from || to) {
    where.timestamp = {}
    if (from) (where.timestamp as Record<string, Date>).gte = new Date(from)
    if (to) (where.timestamp as Record<string, Date>).lte = new Date(to)
  }

  const data = await prisma.timeseries.findMany({
    where,
    orderBy: { timestamp: 'asc' },
    take: 1000,
    select: {
      timestamp: true,
      value: true,
      unit: true,
      qualityFlag: true,
    },
  })

  return NextResponse.json(data)
}
