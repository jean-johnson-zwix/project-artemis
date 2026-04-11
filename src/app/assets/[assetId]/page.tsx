import { notFound } from 'next/navigation'
import prisma from '@/lib/prisma'
import { calculateHealthScore } from '@/lib/health'
import SensorTrendChart from '@/components/assets/SensorTrendChart'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'

export const dynamic = 'force-dynamic'

function healthColor(score: number) {
  if (score >= 80) return 'text-green-400 border-green-500/30 bg-green-500/10'
  if (score >= 50) return 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10'
  return 'text-red-400 border-red-500/30 bg-red-500/10'
}

const severityColors: Record<string, string> = {
  CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOW: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

const priorityColors: Record<string, string> = {
  EMERGENCY: 'bg-red-500/20 text-red-400 border-red-500/30',
  CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOW: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
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
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 mb-1">{asset.tag} · {asset.area}</p>
          <h1 className="text-2xl font-bold text-white">{asset.name}</h1>
          <p className="text-slate-400 text-sm">{asset.type}{asset.subtype ? ` / ${asset.subtype}` : ''}</p>
        </div>
        <div className={cn('border rounded-lg px-4 py-2 text-center', healthColor(healthScore))}>
          <p className="text-2xl font-bold">{healthScore}</p>
          <p className="text-xs opacity-70">Health Score</p>
        </div>
      </div>

      {/* Asset Info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Manufacturer', value: asset.manufacturer },
          { label: 'Model', value: asset.model },
          { label: 'Status', value: asset.status },
          { label: 'Criticality', value: asset.criticality },
          { label: 'Location', value: asset.location },
          { label: 'Install Date', value: asset.installDate ? format(asset.installDate, 'MMM yyyy') : null },
        ].map(({ label, value }) =>
          value ? (
            <div key={label} className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
              <p className="text-xs text-slate-500 mb-1">{label}</p>
              <p className="text-sm text-slate-200">{value}</p>
            </div>
          ) : null
        )}
      </div>

      {/* Sensor Charts */}
      {asset.sensors.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Sensor Trends</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {asset.sensors.map((sensor) => (
              <div key={sensor.id} className="rounded-lg border border-slate-700 bg-slate-900 p-4">
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
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Recent Failures</h2>
          <div className="rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-700">
                <tr>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">Date</th>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">Failure Mode</th>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">Root Cause</th>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">Severity</th>
                </tr>
              </thead>
              <tbody>
                {recentFailures.map((f) => (
                  <tr key={f.id} className="border-b border-slate-800">
                    <td className="px-4 py-2 text-slate-400">{format(f.eventTimestamp, 'MMM d, yyyy')}</td>
                    <td className="px-4 py-2 text-slate-300">{f.failureMode}</td>
                    <td className="px-4 py-2 text-slate-400 max-w-xs truncate">{f.rootCause}</td>
                    <td className="px-4 py-2">
                      <span className={cn('text-xs px-1.5 py-0.5 rounded border', severityColors[f.severity] ?? '')}>
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
          <h2 className="text-sm font-semibold text-slate-300 mb-3">Recent Work Orders</h2>
          <div className="rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-700">
                <tr>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">ID</th>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">Description</th>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">Priority</th>
                  <th className="text-left px-4 py-2 text-slate-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentWorkOrders.map((wo) => (
                  <tr key={wo.id} className="border-b border-slate-800">
                    <td className="px-4 py-2 text-slate-500 font-mono text-xs">{wo.id}</td>
                    <td className="px-4 py-2 text-slate-300 max-w-xs truncate">{wo.workDescription}</td>
                    <td className="px-4 py-2">
                      <span className={cn('text-xs px-1.5 py-0.5 rounded border', priorityColors[wo.priority] ?? '')}>
                        {wo.priority}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-400">{wo.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
