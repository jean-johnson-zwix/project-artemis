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
  OPERATING: 'bg-[#00ff9f]/10 text-[#00ff9f] border-[#00ff9f]/30',
  MAINTENANCE: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  STANDBY: 'bg-[#333333]/20 text-[#999999] border-[#333333]/50',
}

const critColors: Record<string, string> = {
  HIGH: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  MEDIUM: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  LOW: 'bg-[#00d9ff]/10 text-[#00d9ff] border-[#00d9ff]/30',
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
          <div key={i} className="h-24 rounded-sm bg-[#1f2535]/50 animate-pulse border border-[#333333]" />
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
          className="rounded-sm border border-[#333333] bg-[#1f2535]/40 p-3 hover:border-[#00d9ff]/50 hover:bg-[#1f2535]/60 transition-all duration-150 hover:shadow-[0_0_20px_rgba(0,217,255,0.1)]"
        >
          <p className="text-xs text-[#666666] mb-1 uppercase tracking-wider font-semibold">{asset.tag}</p>
          <p className="text-sm font-semibold text-white truncate mb-2">{asset.name}</p>
          <div className="flex gap-1 flex-wrap">
            <span className={`text-xs px-1.5 py-0.5 rounded-sm border ${statusColors[asset.status] ?? ''}`}>
              {asset.status}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded-sm border ${critColors[asset.criticality] ?? ''}`}>
              {asset.criticality}
            </span>
          </div>
          {asset.area && <p className="text-xs text-[#666666] mt-1">{asset.area}</p>}
        </Link>
      ))}
    </div>
  )
}
