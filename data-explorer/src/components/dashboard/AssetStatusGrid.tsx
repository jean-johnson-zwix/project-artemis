'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'

interface Asset {
  id: string
  tag: string
  name: string
  type: string
  status: string
  criticality: string
  area: string | null
}

const statusColors: Record<string, string> = {
  OPERATING: 'bg-green-500/20 text-green-400 border-green-500/30',
  MAINTENANCE: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  STANDBY: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

const critColors: Record<string, string> = {
  HIGH: 'bg-red-500/20 text-red-400 border-red-500/30',
  MEDIUM: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  LOW: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

export default function AssetStatusGrid() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/assets')
      .then((r) => r.json())
      .then((data) => {
        setAssets(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-slate-800 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {assets.slice(0, 24).map((asset) => (
        <Link
          key={asset.id}
          href={`/assets/${encodeURIComponent(asset.id)}`}
          className="rounded-lg border border-slate-700 bg-slate-800/50 p-3 hover:border-orange-500/50 hover:bg-slate-800 transition-colors"
        >
          <p className="text-xs text-slate-500 mb-1">{asset.tag}</p>
          <p className="text-sm font-medium text-slate-100 truncate mb-2">{asset.name}</p>
          <div className="flex gap-1 flex-wrap">
            <span className={`text-xs px-1.5 py-0.5 rounded border ${statusColors[asset.status] ?? ''}`}>
              {asset.status}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded border ${critColors[asset.criticality] ?? ''}`}>
              {asset.criticality}
            </span>
          </div>
          {asset.area && <p className="text-xs text-slate-500 mt-1">{asset.area}</p>}
        </Link>
      ))}
    </div>
  )
}
