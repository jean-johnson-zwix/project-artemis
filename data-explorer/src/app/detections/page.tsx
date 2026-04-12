'use client'

import { useEffect, useState } from 'react'
import { format } from 'date-fns'
import Link from 'next/link'
import { cn } from '@/lib/utils'

interface Detection {
  id: string
  detectedAt: string
  detectionType: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  assetId: string
  assetTag: string
  assetName: string
  area: string
  resolvedAt: string | null
}

const severityColors: Record<string, string> = {
  CRITICAL: 'bg-red-500/10 text-red-400 border-red-500/30',
  HIGH:     'bg-orange-500/10 text-orange-400 border-orange-500/30',
  MEDIUM:   'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  LOW:      'bg-[#00d9ff]/10 text-[#00d9ff] border-[#00d9ff]/30',
}

export default function DetectionsPage() {
  const [detections, setDetections] = useState<Detection[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    severity: '',
    type: '',
    asset: '',
    resolved: '',
  })

  useEffect(() => {
    fetch('/api/detections?limit=200')
      .then((r) => r.json())
      .then((data) => {
        setDetections(data as Detection[])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const filtered = detections.filter((d) => {
    if (filters.severity && d.severity !== filters.severity) return false
    if (filters.type && d.detectionType !== filters.type) return false
    if (filters.asset && !d.assetName.toLowerCase().includes(filters.asset.toLowerCase())) return false
    if (filters.resolved === 'open' && d.resolvedAt !== null) return false
    if (filters.resolved === 'resolved' && d.resolvedAt === null) return false
    return true
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e]">
      <div className="p-6 max-w-full">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white tracking-tight">Detections</h1>
          <p className="text-[#999999] text-sm mt-2">Full list of all pipeline detections</p>
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
              <option value="CORROSION_THRESHOLD">Corrosion Threshold</option>
              <option value="SENSOR_ANOMALY">Sensor Anomaly</option>
              <option value="TRANSMITTER_DIVERGENCE">Transmitter Divergence</option>
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
            <label className="text-xs text-[#999999] uppercase tracking-wider font-semibold block mb-2">Status</label>
            <select
              value={filters.resolved}
              onChange={(e) => setFilters({ ...filters, resolved: e.target.value })}
              className="w-full bg-[#0f1419] border border-[#333333] rounded-sm px-2 py-1 text-white text-sm"
            >
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="resolved">Resolved</option>
            </select>
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
                  <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Asset</th>
                  <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Area</th>
                  <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Severity</th>
                  <th className="text-left px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Status</th>
                  <th className="text-right px-4 py-3 text-[#999999] font-semibold uppercase text-xs tracking-wider">Detected</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => (
                  <tr key={d.id} className="border-b border-[#1f2535] hover:bg-[#1f2535]/40 transition-colors">
                    <td className="px-4 py-3">
                      <Link href={`/detections/${d.id}`} className="text-xs px-2 py-1 rounded-sm border border-[#333333] text-[#999999] hover:text-white hover:border-[#555555] transition-colors">
                        {d.detectionType.replace(/_/g, ' ')}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/assets/${d.assetId}`} className="text-[#00d9ff] hover:underline font-medium">
                        {d.assetName}
                      </Link>
                      <span className="text-[#555555] text-xs ml-2">{d.assetTag}</span>
                    </td>
                    <td className="px-4 py-3 text-[#999999]">{d.area}</td>
                    <td className="px-4 py-3">
                      <span className={cn('text-xs px-2 py-1 rounded-sm border', severityColors[d.severity] || '')}>
                        {d.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {d.resolvedAt ? (
                        <span className="text-xs px-2 py-1 rounded-sm border border-green-500/30 text-green-400 bg-green-500/10">
                          Resolved
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-1 rounded-sm border border-[#ff6b35]/30 text-[#ff6b35] bg-[#ff6b35]/10">
                          Open
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-[#666666]">
                      {format(new Date(d.detectedAt), 'MMM d HH:mm')}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-[#555555] text-sm italic">
                      No detections match the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
