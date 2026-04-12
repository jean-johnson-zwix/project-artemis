import { notFound } from 'next/navigation'
import prisma from '@/lib/prisma'
import { calculateHealthScore } from '@/lib/health'
import SensorTrendChart from '@/components/assets/SensorTrendChart'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'
import Link from 'next/link'

export const dynamic = 'force-dynamic'

function healthColor(score: number) {
  if (score >= 80) return 'text-[#00ff9f] border-[#00ff9f]/30 bg-[#00ff9f]/10'
  if (score >= 50) return 'text-[#ff6b35] border-[#ff6b35]/30 bg-[#ff6b35]/10'
  return 'text-[#ff6b35] border-[#ff6b35]/30 bg-[#ff6b35]/10'
}

const severityColors: Record<string, string> = {
  CRITICAL: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  HIGH: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  MEDIUM: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  LOW: 'bg-[#00d9ff]/10 text-[#00d9ff] border-[#00d9ff]/30',
}

const priorityColors: Record<string, string> = {
  EMERGENCY: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  CRITICAL: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  HIGH: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  MEDIUM: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  LOW: 'bg-[#00d9ff]/10 text-[#00d9ff] border-[#00d9ff]/30',
}

export default async function AssetDetailPage({
  params,
}: {
  params: Promise<{ assetId: string }>
}) {
  const { assetId } = await params
  const decodedId = decodeURIComponent(assetId)

  const asset = await prisma.asset.findUnique({
    where: { id: decodedId },
    include: { sensors: true },
  })

  if (!asset) notFound()

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)

  const [recentFailures, recentWorkOrders, openWorkOrders, recentFailureCount] = await Promise.all([
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
    prisma.failureEvent.count({
      where: { assetId: decodedId, eventTimestamp: { gte: thirtyDaysAgo } },
    }),
  ])

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e]">
      <div className="p-6 max-w-full">
        <Link href="/dashboard" className="text-[#00d9ff] hover:text-[#00d9ff] underline text-sm mb-4 inline-block">
          ← Back to Dashboard
        </Link>
        <div className="mb-8 flex items-start justify-between">
          <div>
            <p className="text-xs text-[#999999] mb-2 uppercase tracking-wider font-semibold">{asset.tag} · {asset.area}</p>
            <h1 className="text-4xl font-bold text-white tracking-tight">{asset.name}</h1>
            <p className="text-[#999999] text-sm mt-2">{asset.type}{asset.subtype ? ` / ${asset.subtype}` : ''}</p>
          </div>
          <div className={cn('border rounded-sm px-6 py-3 text-center', healthColor(healthScore))}>
            <p className="text-3xl font-bold">{healthScore}</p>
            <p className="text-xs opacity-70 uppercase tracking-wider font-semibold mt-1">Health Score</p>
          </div>
        </div>

        {/* Asset Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Manufacturer', value: asset.manufacturer },
            { label: 'Model', value: asset.model },
            { label: 'Status', value: asset.status },
            { label: 'Criticality', value: asset.criticality },
            { label: 'Location', value: asset.location },
            { label: 'Install Date', value: asset.installDate ? format(asset.installDate, 'MMM yyyy') : null },
          ].map(({ label, value }) =>
            value ? (
              <div key={label} className="rounded-sm border border-[#333333] bg-[#1f2535]/40 p-4">
                <p className="text-xs text-[#999999] mb-2 uppercase tracking-wider font-semibold">{label}</p>
                <p className="text-white font-semibold">{value}</p>
              </div>
            ) : null
          )}
        </div>

        {/* Sensor Charts */}
        {asset.sensors.length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4">Sensor Trends</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {asset.sensors.map((sensor) => (
                <div key={sensor.id} className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
                  <SensorTrendChart
                    sensorId={sensor.id}
                    sensorName={sensor.name}
                    unit={sensor.unit}
                    normalMin={sensor.normalMin}
                    normalMax={sensor.normalMax}
                    alarmLow={sensor.alarmLow}
                    alarmHigh={sensor.alarmHigh}
                    tripLow={sensor.tripLow}
                    tripHigh={sensor.tripHigh}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Failures */}
        {recentFailures.length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4">Recent Failures</h2>
            <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="border-b border-[#333333]">
                  <tr>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Date</th>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Failure Mode</th>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Root Cause</th>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {recentFailures.map((f) => (
                    <tr key={f.id} className="border-b border-[#1f2535] hover:bg-[#1f2535]/40 transition-colors">
                      <td className="px-4 py-3 text-[#999999]">{format(f.eventTimestamp, 'MMM d, yyyy')}</td>
                      <td className="px-4 py-3 text-white font-semibold">{f.failureMode}</td>
                      <td className="px-4 py-3 text-[#666666] max-w-xs truncate">{f.rootCause}</td>
                      <td className="px-4 py-3">
                        <span className={cn('text-xs px-2 py-1 rounded-sm border', severityColors[f.severity] ?? '')}>
                          {f.severity}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Recent Work Orders */}
        {recentWorkOrders.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4">Recent Work Orders</h2>
            <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="border-b border-[#333333]">
                  <tr>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">ID</th>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Description</th>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Priority</th>
                    <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentWorkOrders.map((wo) => (
                    <tr key={wo.id} className="border-b border-[#1f2535] hover:bg-[#1f2535]/40 transition-colors">
                      <td className="px-4 py-3 text-[#666666] font-mono text-xs">{wo.id}</td>
                      <td className="px-4 py-3 text-white max-w-xs truncate">{wo.workDescription}</td>
                      <td className="px-4 py-3">
                        <span className={cn('text-xs px-2 py-1 rounded-sm border', priorityColors[wo.priority] ?? '')}>
                          {wo.priority}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[#999999]">{wo.status}</td>
                    </tr>
                  ))}
                </tbody>
            </table>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}
