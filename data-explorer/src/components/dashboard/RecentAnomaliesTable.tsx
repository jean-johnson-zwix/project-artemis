'use client'

import { useEffect, useState } from 'react'
import { format } from 'date-fns'
import Link from 'next/link'

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
  TRIP_HIGH: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  TRIP_LOW: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  ALARM_HIGH: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  ALARM_LOW: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
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
    return <div className="h-40 bg-[#1f2535]/50 animate-pulse rounded-sm border border-[#333333]" />
  }

  if (anomalies.length === 0) {
    return <p className="text-[#666666] text-sm text-center py-8">No recent anomalies</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#333333]">
            <th className="text-left py-3 px-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Type</th>
            <th className="text-left py-3 px-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Sensor</th>
            <th className="text-right py-3 px-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Time</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((a, i) => (
            <tr key={`${a.sensorId}-${i}`} className="border-b border-[#1f2535] hover:bg-[#1f2535]/40 transition-colors">
              <td className="py-3 px-3">
                <span className={`text-xs px-1.5 py-0.5 rounded-sm border font-semibold ${anomalyColors[a.anomalyType] ?? ''}`}>
                  {a.anomalyType}
                </span>
              </td>
              <td className="py-3 px-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-white">{a.sensorName}</span>
                  <Link href={`/assets/${encodeURIComponent(a.assetId)}`} className="text-[#00d9ff] hover:text-[#00d9ff] underline font-medium text-xs">
                    {a.assetName}
                  </Link>
                </div>
              </td>
              <td className="py-3 px-3 text-right text-[#666666]">
                {format(new Date(a.timestamp), 'MMM d HH:mm')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
