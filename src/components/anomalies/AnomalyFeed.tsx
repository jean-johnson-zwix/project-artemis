'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'

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

const anomalyStyles: Record<string, { badge: string; label: string }> = {
  TRIP_HIGH: { badge: 'bg-red-500/20 text-red-400 border-red-500/30', label: 'TRIP HIGH' },
  TRIP_LOW: { badge: 'bg-red-500/20 text-red-400 border-red-500/30', label: 'TRIP LOW' },
  ALARM_HIGH: { badge: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', label: 'ALARM HIGH' },
  ALARM_LOW: { badge: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', label: 'ALARM LOW' },
}

export default function AnomalyFeed({ limit = 100 }: { limit?: number }) {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/anomalies?limit=${limit}`)
      .then((r) => r.json())
      .then((data) => {
        setAnomalies(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [limit])

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 bg-slate-800 animate-pulse rounded-lg" />
        ))}
      </div>
    )
  }

  if (anomalies.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <p className="text-lg">No anomalies detected</p>
        <p className="text-sm mt-1">All sensors within threshold limits</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {anomalies.map((a, i) => {
        const style = anomalyStyles[a.anomalyType] ?? { badge: '', label: a.anomalyType }
        const isTrip = a.anomalyType.startsWith('TRIP')
        return (
          <div
            key={`${a.sensorId}-${i}`}
            className={cn(
              'rounded-lg border p-4',
              isTrip ? 'border-red-500/30 bg-red-500/5' : 'border-yellow-500/30 bg-yellow-500/5'
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn('text-xs px-1.5 py-0.5 rounded border font-medium', style.badge)}>
                    {style.label}
                  </span>
                  <span className="text-xs text-slate-500">{format(new Date(a.timestamp), 'MMM d, yyyy HH:mm')}</span>
                </div>
                <p className="text-sm font-medium text-slate-200">{a.sensorName}</p>
                <Link
                  href={`/assets/${encodeURIComponent(a.assetId)}`}
                  className="text-xs text-slate-400 hover:text-orange-400"
                >
                  {a.assetName}
                </Link>
              </div>
              <div className="text-right flex-shrink-0">
                <p className={cn('text-lg font-bold', isTrip ? 'text-red-400' : 'text-yellow-400')}>
                  {a.value.toFixed(2)}
                  <span className="text-xs ml-1 opacity-70">{a.unit}</span>
                </p>
                <p className="text-xs text-slate-500">
                  Threshold: {a.threshold.toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
