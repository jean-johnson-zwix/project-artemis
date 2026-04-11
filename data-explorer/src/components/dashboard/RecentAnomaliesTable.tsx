'use client'

import { useEffect, useState } from 'react'
import { format } from 'date-fns'

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

const anomalyColors: Record<string, string> = {
  TRIP_HIGH: 'bg-red-500/20 text-red-400 border-red-500/30',
  TRIP_LOW: 'bg-red-500/20 text-red-400 border-red-500/30',
  ALARM_HIGH: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  ALARM_LOW: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
}

export default function RecentAnomaliesTable() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/anomalies?limit=10')
      .then((r) => r.json())
      .then((data) => {
        setAnomalies(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="h-40 bg-slate-800 animate-pulse rounded-lg" />
  }

  if (anomalies.length === 0) {
    return <p className="text-slate-500 text-sm text-center py-8">No recent anomalies</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            <th className="text-left py-2 px-3 text-slate-400 font-medium">Type</th>
            <th className="text-left py-2 px-3 text-slate-400 font-medium">Sensor</th>
            <th className="text-left py-2 px-3 text-slate-400 font-medium">Asset</th>
            <th className="text-right py-2 px-3 text-slate-400 font-medium">Value</th>
            <th className="text-right py-2 px-3 text-slate-400 font-medium">Threshold</th>
            <th className="text-right py-2 px-3 text-slate-400 font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((a, i) => (
            <tr key={`${a.sensorId}-${i}`} className="border-b border-slate-800 hover:bg-slate-800/50">
              <td className="py-2 px-3">
                <span className={`text-xs px-1.5 py-0.5 rounded border ${anomalyColors[a.anomalyType] ?? ''}`}>
                  {a.anomalyType}
                </span>
              </td>
              <td className="py-2 px-3 text-slate-300">{a.sensorName}</td>
              <td className="py-2 px-3 text-slate-400">{a.assetName}</td>
              <td className="py-2 px-3 text-right text-slate-300">
                {a.value.toFixed(2)} {a.unit}
              </td>
              <td className="py-2 px-3 text-right text-slate-500">
                {a.threshold.toFixed(2)}
              </td>
              <td className="py-2 px-3 text-right text-slate-500">
                {format(new Date(a.timestamp), 'MMM d HH:mm')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
