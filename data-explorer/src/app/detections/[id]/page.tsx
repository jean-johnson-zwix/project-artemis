import { notFound } from 'next/navigation'
import Link from 'next/link'
import prisma from '@/lib/prisma'
import { format } from 'date-fns'
import SensorTrendChart from '@/components/assets/SensorTrendChart'

export const dynamic = 'force-dynamic'

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/30',
  HIGH:     'text-orange-400 bg-orange-500/10 border-orange-500/30',
  MEDIUM:   'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  LOW:      'text-blue-400 bg-blue-500/10 border-blue-500/30',
}

const CONFIDENCE_STYLES: Record<string, string> = {
  HIGH:   'text-green-400 bg-green-500/10 border-green-500/30',
  MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  LOW:    'text-[#999999] bg-[#1f2535]/60 border-[#444444]',
}

export default async function DetectionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const decodedId = decodeURIComponent(id)

  const detection = await prisma.detection.findUnique({
    where: { id: decodedId },
    include: { insight: true },
  })

  if (!detection) {
    notFound()
  }

  const insight = detection.insight
  const dd = detection.detectionData as Record<string, unknown>
  const isCorrosion = detection.detectionType === 'CORROSION_THRESHOLD'

  // Resolve the primary sensor for the trend chart
  const sensorId =
    (dd.sensor_id as string | undefined) ??
    (dd.temp_sensor_id as string | undefined) ??
    (dd.sensor_a_id as string | undefined)

  const sensor = sensorId
    ? await prisma.sensorMetadata.findUnique({ where: { id: sensorId } })
    : null

  const remainingLife = insight?.remainingLifeYears ?? null
  const lifeGaugePct = remainingLife !== null ? Math.min(100, (remainingLife / 10) * 100) : null
  const lifeColor =
    remainingLife === null ? ''
    : remainingLife < 2   ? 'text-red-400'
    : remainingLife < 3   ? 'text-orange-400'
                          : 'text-yellow-400'
  const lifeBarColor =
    remainingLife === null ? ''
    : remainingLife < 2   ? 'bg-red-500'
    : remainingLife < 3   ? 'bg-orange-500'
                          : 'bg-yellow-500'

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e]">
      <div className="p-6 max-w-4xl mx-auto">

        {/* Back link */}
        <Link
          href="/detections"
          className="text-xs text-[#999999] hover:text-white uppercase tracking-wider mb-6 inline-block"
        >
          ← Back to Detections
        </Link>

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-[#999999] mb-2 uppercase tracking-wider font-semibold">
                {detection.assetTag} · {detection.detectionType.replace(/_/g, ' ')}
              </p>
              <h1 className="text-3xl font-bold text-white tracking-tight">Detection Details</h1>
              <p className="text-[#999999] text-sm mt-2">
                Detected {format(new Date(detection.detectedAt), 'MMM d, yyyy HH:mm')} UTC
              </p>
            </div>

            <div className="flex flex-col items-end gap-2 mt-1">
              <span
                className={`text-xs px-3 py-1.5 rounded-sm border font-bold tracking-wider ${
                  SEVERITY_STYLES[detection.severity] ?? ''
                }`}
              >
                {detection.severity}
              </span>
              {insight && (
                <span
                  className={`text-xs px-3 py-1.5 rounded-sm border ${
                    CONFIDENCE_STYLES[insight.confidence] ?? ''
                  }`}
                >
                  Confidence: {insight.confidence}
                </span>
              )}
              {!insight && (
                <span className="text-xs px-3 py-1.5 rounded-sm border border-[#444444] text-[#666666] animate-pulse">
                  AI analysing…
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Remaining-life gauge — corrosion only */}
        {isCorrosion && remainingLife !== null && (
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6 mb-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">
              Estimated Remaining Asset Life
            </h2>
            <div className="flex items-center gap-6">
              <div className="text-center min-w-[80px]">
                <p className={`text-5xl font-bold tabular-nums ${lifeColor}`}>
                  {remainingLife.toFixed(1)}
                </p>
                <p className="text-[#999999] text-xs mt-1">years</p>
              </div>
              <div className="flex-1">
                <div className="h-3 bg-[#2a2a3a] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${lifeBarColor}`}
                    style={{ width: `${lifeGaugePct}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-[#555555] mt-1">
                  <span>0 yr</span>
                  <span>10 yr</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* What / Why / Evidence */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">

          {/* What */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">
              What
            </h2>
            {insight ? (
              <p className="text-white text-sm leading-relaxed">{insight.what}</p>
            ) : (
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">
                    Detection Type
                  </p>
                  <p className="text-white font-semibold">
                    {detection.detectionType.replace(/_/g, ' ')}
                  </p>
                </div>
                <p className="text-[#555555] text-xs italic mt-3">
                  AI insight generating — refresh in a few seconds.
                </p>
              </div>
            )}
          </div>

          {/* Why */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">
              Why
            </h2>
            {insight ? (
              <p className="text-white text-sm leading-relaxed">{insight.why}</p>
            ) : (
              <p className="text-[#555555] text-xs italic">AI analysis in progress…</p>
            )}
          </div>

          {/* Evidence */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">
              Evidence
            </h2>
            {insight ? (
              <ul className="space-y-2">
                {(insight.evidence as string[]).map((e, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-white">
                    <span className="text-[#00d9ff] mt-0.5 shrink-0">•</span>
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Asset</p>
                  <p className="text-white">{detection.assetName}</p>
                </div>
                <div>
                  <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1">Detected</p>
                  <p className="text-white">{format(new Date(detection.detectedAt), 'MMM d, yyyy HH:mm:ss')}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sensor Trend Chart */}
        {sensor && (
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6 mb-6">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">
              Sensor Trend
            </h2>
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
        )}

        {/* Recommended Actions */}
        <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6 mb-6">
          <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 pb-3 border-b border-[#333333]">
            Recommended Actions
          </h2>
          {insight ? (
            <div className="space-y-2">
              {(insight.recommendedActions as string[]).map((action, i) => (
                <label
                  key={i}
                  className="flex items-center gap-3 p-2 rounded-sm hover:bg-[#1f2535]/40 cursor-pointer"
                >
                  <input type="checkbox" className="w-4 h-4 rounded" />
                  <span className="text-sm text-[#cccccc]">{action}</span>
                </label>
              ))}
            </div>
          ) : (
            <p className="text-[#555555] text-sm italic">
              Recommended actions will appear once AI analysis completes.
            </p>
          )}
        </div>

        {/* Asset link */}
        <Link
          href={`/assets/${detection.assetId}`}
          className="text-[#00d9ff] text-sm hover:underline"
        >
          View Asset: {detection.assetName} →
        </Link>
      </div>
    </div>
  )
}
