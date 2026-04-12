import { notFound } from 'next/navigation'
import prisma from '@/lib/prisma'
import { format } from 'date-fns'
import SensorTrendChart from '@/components/assets/SensorTrendChart'

export const dynamic = 'force-dynamic'

interface Anomaly {
  sensorId: string
  sensorName: string
  assetId: string
  assetName: string
  timestamp: string
  value: number
  unit: string
  anomalyType: string
  threshold: number
}

export default async function DetectionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const decodedId = decodeURIComponent(id)

  // Fetch sensor details (SensorMetadata model)
  const sensor = await prisma.sensorMetadata.findUnique({
    where: { id: decodedId },
    include: { asset: true },
  })

  if (!sensor) {
    notFound()
  }

  const asset = sensor.asset

  // Fetch latest timeseries data to show as detection
  const latestReading = await prisma.timeseries.findFirst({
    where: { sensorId: decodedId },
    orderBy: { timestamp: 'desc' },
    take: 1,
  })

  if (!latestReading) {
    notFound()
  }

  const anomaly = {
    sensorId: sensor.id,
    sensorName: sensor.name,
    assetId: asset.id,
    assetName: asset.name,
    timestamp: latestReading.timestamp.toISOString(),
    value: latestReading.value,
    unit: sensor.unit,
    anomalyType: latestReading.value > (sensor.tripHigh || sensor.alarmHigh || 0) ? 'TRIP_HIGH' : 'ALARM_HIGH',
    threshold: sensor.alarmHigh || 0,
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e]">
      <div className="p-6 max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xs text-[#999999] mb-2 uppercase tracking-wider font-semibold">{asset.tag} · {sensor.name}</p>
              <h1 className="text-3xl font-bold text-white tracking-tight">Detection Details</h1>
              <p className="text-[#999999] text-sm mt-2">{anomaly.anomalyType} threshold breach on {format(new Date(anomaly.timestamp), 'MMM d, yyyy HH:mm')}</p>
            </div>
          </div>
        </div>

        {/* What / Why / Evidence Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* What */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">What</h2>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Anomaly Type</p>
                <p className="text-white font-semibold">{anomaly.anomalyType}</p>
              </div>
              <div>
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Current Value</p>
                <p className="text-2xl font-bold text-[#ff6b35]">{anomaly.value.toFixed(2)} {sensor.unit}</p>
              </div>
              <div>
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Threshold</p>
                <p className="text-white">{anomaly.threshold?.toFixed(2) || 'N/A'} {sensor.unit}</p>
              </div>
            </div>
          </div>

          {/* Why */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">Why</h2>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Contributing Factor</p>
                <p className="text-white">Sensor reading exceeded configured threshold</p>
              </div>
              <div>
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Potential Cause</p>
                <p className="text-[#999999] text-sm">Asset may require maintenance or operating parameters have changed</p>
              </div>
            </div>
          </div>

          {/* Evidence */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">Evidence</h2>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Asset</p>
                <p className="text-white">{asset.name}</p>
              </div>
              <div>
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Detected</p>
                <p className="text-white">{format(new Date(anomaly.timestamp), 'MMM d, yyyy HH:mm:ss')}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Sensor Trend Chart */}
        <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6 mb-6">
          <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">Sensor Trend</h2>
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

        {/* Recommended Actions */}
        <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
          <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">Recommended Actions</h2>
          <div className="space-y-2">
            {[
              'Review sensor calibration and accuracy',
              'Check asset operating parameters',
              'Inspect physical asset condition',
              'Create maintenance work order if needed',
              'Escalate to operations team',
            ].map((action, i) => (
              <label key={i} className="flex items-center gap-3 p-2 rounded-sm hover:bg-[#1f2535]/40 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded" />
                <span className="text-sm text-[#999999]">{action}</span>
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
