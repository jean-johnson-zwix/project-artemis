import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const limit = parseInt(searchParams.get('limit') ?? '100')

  // Get all sensors with thresholds
  const sensors = await prisma.sensorMetadata.findMany({
    where: {
      OR: [
        { alarmHigh: { not: null } },
        { alarmLow: { not: null } },
        { tripHigh: { not: null } },
        { tripLow: { not: null } },
      ],
    },
    include: { asset: { select: { id: true, name: true } } },
  })

  const anomalies = []

  for (const sensor of sensors) {
    // Get recent readings that breach thresholds
    const conditions: Array<Record<string, unknown>> = []

    if (sensor.alarmHigh !== null) conditions.push({ value: { gt: sensor.alarmHigh } })
    if (sensor.alarmLow !== null) conditions.push({ value: { lt: sensor.alarmLow } })
    if (sensor.tripHigh !== null) conditions.push({ value: { gt: sensor.tripHigh } })
    if (sensor.tripLow !== null) conditions.push({ value: { lt: sensor.tripLow } })

    if (conditions.length === 0) continue

    const breaches = await prisma.timeseries.findMany({
      where: {
        sensorId: sensor.id,
        OR: conditions,
      },
      orderBy: { timestamp: 'desc' },
      take: 5,
    })

    for (const breach of breaches) {
      let anomalyType: string
      let threshold: number

      if (sensor.tripHigh !== null && breach.value > sensor.tripHigh) {
        anomalyType = 'TRIP_HIGH'
        threshold = sensor.tripHigh
      } else if (sensor.tripLow !== null && breach.value < sensor.tripLow) {
        anomalyType = 'TRIP_LOW'
        threshold = sensor.tripLow
      } else if (sensor.alarmHigh !== null && breach.value > sensor.alarmHigh) {
        anomalyType = 'ALARM_HIGH'
        threshold = sensor.alarmHigh
      } else {
        anomalyType = 'ALARM_LOW'
        threshold = sensor.alarmLow!
      }

      anomalies.push({
        sensorId: sensor.id,
        sensorName: sensor.name,
        assetId: sensor.assetId,
        assetName: sensor.asset.name,
        timestamp: breach.timestamp,
        value: breach.value,
        unit: sensor.unit,
        anomalyType,
        threshold,
      })
    }

    if (anomalies.length >= limit) break
  }

  anomalies.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  return NextResponse.json(anomalies.slice(0, limit))
}
