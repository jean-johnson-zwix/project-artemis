import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/prisma'
import { calculateHealthScore } from '@/lib/health'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ assetId: string }> }
) {
  const { assetId } = await params
  const decodedId = decodeURIComponent(assetId)

  const asset = await prisma.asset.findUnique({
    where: { id: decodedId },
    include: {
      sensors: true,
      children: true,
      parent: true,
    },
  })

  if (!asset) {
    return NextResponse.json({ error: 'Asset not found' }, { status: 404 })
  }

  const [recentFailures, recentWorkOrders, openWorkOrders] = await Promise.all([
    prisma.failureEvent.findMany({
      where: { assetId: decodedId },
      orderBy: { eventTimestamp: 'desc' },
      take: 5,
    }),
    prisma.workOrder.findMany({
      where: { assetId: decodedId },
      orderBy: { raisedDate: 'desc' },
      take: 5,
    }),
    prisma.workOrder.count({
      where: { assetId: decodedId, status: { in: ['OPEN', 'IN_PROGRESS'] } },
    }),
  ])

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
  const recentFailureCount = await prisma.failureEvent.count({
    where: { assetId: decodedId, eventTimestamp: { gte: thirtyDaysAgo } },
  })

  // Get latest sensor values
  const latestValues = new Map<string, number>()
  for (const sensor of asset.sensors) {
    const latest = await prisma.timeseries.findFirst({
      where: { sensorId: sensor.id },
      orderBy: { timestamp: 'desc' },
    })
    if (latest) latestValues.set(sensor.id, latest.value)
  }

  const healthScore = calculateHealthScore({
    sensors: asset.sensors,
    latestValues,
    openWorkOrders,
    recentFailures: recentFailureCount,
  })

  return NextResponse.json({
    ...asset,
    recentFailures,
    recentWorkOrders,
    healthScore,
  })
}
