import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const limit = parseInt(searchParams.get('limit') ?? '100')

  const detections = await prisma.detection.findMany({
    orderBy: { detectedAt: 'desc' },
    take: limit,
    select: {
      id: true,
      detectedAt: true,
      detectionType: true,
      severity: true,
      assetId: true,
      assetTag: true,
      assetName: true,
      area: true,
      resolvedAt: true,
    },
  })

  return NextResponse.json(detections)
}
