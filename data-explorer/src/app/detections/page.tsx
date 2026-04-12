'use client'

import { useEffect, useState } from 'react'
import { format } from 'date-fns'
import Link from 'next/link'
import { cn } from '@/lib/utils'

interface Detection {
  sensorId: string
  sensorName: string
  assetId: string
  assetName: string
  timestamp: string
  value: number
  unit: string
  anomalyType: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  threshold: number
}

const severityColors: Record<string, string> = {
  CRITICAL: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  HIGH: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  MEDIUM: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  LOW: 'bg-[#00d9ff]/10 text-[#00d9ff] border-[#00d9ff]/30',
}

const typeColors: Record<string, string> = {
  TRIP_HIGH: 'bg-red-500/20 text-red-400',
  TRIP_LOW: 'bg-red-500/20 text-red-400',
  ALARM_HIGH: 'bg-orange-500/20 text-orange-400',
  ALARM_LOW: 'bg-orange-500/20 text-orange-400',
}

export default function DetectionsPage() {
  const [detections, setDetections] = useState<Detection[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    severity: '',
    type: '',
    asset: '',
    startDate: '',
  })

  useEffect(() => {
    fetch('/api/anomalies?limit=100')
      .then((r) => r.json())
      .then((data) => {
        setDetections(data as Detection[])
        console.log(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const filtered = detections.filter((d) => {
    if (filters.severity && d.severity !== filters.severity) return false
    if (filters.type && d.anomalyType !== filters.type) return false
    if (filters.asset && !d.assetName.toLowerCase().includes(filters.asset.toLowerCase())) return false
    return true
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e]">
      <div className="p-6 max-w-full">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white tracking-tight">Detections</h1>
          <p className="text-[#999999] text-sm mt-2">Full list of all threshold breaches and anomalies</p>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/40 p-3">
            <label className="text-xs text-[#999999] uppercase tracking-wider font-semibold block mb-2">Severity</label>
            <select
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              className="w-full bg-[#0f1419] border border-[#333333] rounded-sm px-2 py-1 text-white text-sm"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/40 p-3">
            <label className="text-xs text-[#999999] uppercase tracking-wider font-semibold block mb-2">Type</label>
            <select
              value={filters.type}
              onChange={(e) => setFilters({ ...filters, type: e.target.value })}
              className="w-full bg-[#0f1419] border border-[#333333] rounded-sm px-2 py-1 text-white text-sm"
            >
              <option value="">All Types</option>
              <option value="TRIP_HIGH">Trip High</option>
              <option value="TRIP_LOW">Trip Low</option>
              <option value="ALARM_HIGH">Alarm High</option>
              <option value="ALARM_LOW">Alarm Low</option>
            </select>
          </div>

          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/40 p-3">
            <label className="text-xs text-[#999999] uppercase tracking-wider font-semibold block mb-2">Asset</label>
            <input
              type="text"
              value={filters.asset}
              onChange={(e) => setFilters({ ...filters, asset: e.target.value })}
              placeholder="Search asset..."
              className="w-full bg-[#0f1419] border border-[#333333] rounded-sm px-2 py-1 text-white text-sm placeholder-[#666666]"
            />
          </div>

          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/40 p-3">
            <label className="text-xs text-[#999999] uppercase tracking-wider font-semibold block mb-2">Start Date</label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
              className="w-full bg-[#0f1419] border border-[#333333] rounded-sm px-2 py-1 text-white text-sm"
            />
          </div>
        </div>

        {/* Detections Table */}
        {loading ? (
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 p-6">
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-12 bg-[#1f2535]/50 animate-pulse rounded-sm" />
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-[#333333]">
                <tr>
                  <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Type</th>
                  <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Sensor</th>
                  <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Asset</th>
                  <th className="text-right px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Value</th>
                  <th className="text-right px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Threshold</th>
                  <th className="text-right px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Severity</th>
                  <th className="text-right px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Time</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d, i) => (
                  <tr key={`${d.sensorId}-${i}`} className="border-b border-[#1f2535] hover:bg-[#1f2535]/40 transition-colors">
                    <td className="px-4 py-3">
                      <span className="text-xs px-2 py-1 rounded-sm border border-[#333333] text-[#999999]">
                        {d.anomalyType}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-white font-medium">{d.sensorName}</td>
                    <td className="px-4 py-3">
                      <Link href={`/assets/${d.assetId}`} className="text-[#00d9ff] hover:text-[#00d9ff] underline">
                        {d.assetName}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-right text-white font-semibold">
                      {d.value.toFixed(2)} {d.unit}
                    </td>
                    <td className="px-4 py-3 text-right text-[#666666]">{d.threshold.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={cn('text-xs px-2 py-1 rounded-sm border', severityColors[d.severity] || '')}>
                        {d.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-[#666666]">
                      {format(new Date(d.timestamp), 'MMM d HH:mm')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
