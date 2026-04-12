'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'

interface Asset {
  id: string
  tag: string
  name: string
  type: string
  status: string
  criticality: string
  area: string | null
}

const statusOrder: Record<string, number> = {
  MAINTENANCE: 0,
  STANDBY: 1,
  OPERATING: 2,
}

const critOrder: Record<string, number> = {
  HIGH: 0,
  MEDIUM: 1,
  LOW: 2,
}

const statusColors: Record<string, string> = {
  OPERATING: 'bg-[#00ff9f]/10 text-[#00ff9f] border-[#00ff9f]/30',
  MAINTENANCE: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  STANDBY: 'bg-[#333333]/20 text-[#999999] border-[#333333]/50',
}

const critColors: Record<string, string> = {
  HIGH: 'bg-[#ff4444]/10 text-[#ff4444] border-[#ff4444]/30',
  MEDIUM: 'bg-[#ff6b35]/10 text-[#ff6b35] border-[#ff6b35]/30',
  LOW: 'bg-[#00d9ff]/10 text-[#00d9ff] border-[#00d9ff]/30',
}

const statusTooltips: Record<string, string> = {
  OPERATING: 'Asset is currently running in normal operation.',
  MAINTENANCE: 'Asset is under maintenance and may require urgent attention.',
  STANDBY: 'Asset is idle and not currently in use.',
}

const critTooltips: Record<string, string> = {
  HIGH: 'High criticality — failure of this asset has major operational impact.',
  MEDIUM: 'Medium criticality — failure causes moderate disruption.',
  LOW: 'Low criticality — failure has minimal operational impact.',
}

function sortAssets(assets: Asset[]): Asset[] {
  return [...assets].sort((a, b) => {
    const statusDiff = (statusOrder[a.status] ?? 99) - (statusOrder[b.status] ?? 99)
    if (statusDiff !== 0) return statusDiff
    return (critOrder[a.criticality] ?? 99) - (critOrder[b.criticality] ?? 99)
  })
}

export default function AssetStatusGrid() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/assets')
      .then((r) => r.json())
      .then((data) => {
        setAssets(sortAssets(data))
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
      {assets.map((asset) => (
        <Link
          key={asset.id}
          href={`/assets/${encodeURIComponent(asset.id)}`}
          className="rounded-sm border border-[#333333] bg-[#1f2535]/40 p-3 hover:border-[#00d9ff]/50 hover:bg-[#1f2535]/60 transition-all duration-150 hover:shadow-[0_0_20px_rgba(0,217,255,0.1)]"
        >
          <Tooltip>
            <TooltipTrigger
              render={<p className="text-xs text-[#666666] mb-1 uppercase tracking-wider font-semibold truncate" />}
            >
              {asset.tag}
            </TooltipTrigger>
            <TooltipContent>{asset.tag}</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={<p className="text-sm font-semibold text-white truncate mb-2" />}
            >
              {asset.name}
            </TooltipTrigger>
            <TooltipContent>{asset.name}</TooltipContent>
          </Tooltip>

          <div className="flex flex-col gap-1">
            <Tooltip>
              <TooltipTrigger
                render={
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded-sm border w-fit ${statusColors[asset.status] ?? ''}`}
                  />
                }
              >
                {asset.status}
              </TooltipTrigger>
              <TooltipContent>{statusTooltips[asset.status] ?? asset.status}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger
                render={
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded-sm border w-fit ${critColors[asset.criticality] ?? ''}`}
                  />
                }
              >
                {asset.criticality}
              </TooltipTrigger>
              <TooltipContent>{critTooltips[asset.criticality] ?? asset.criticality}</TooltipContent>
            </Tooltip>
          </div>

          {asset.area && (
            <Tooltip>
              <TooltipTrigger
                render={<p className="text-xs text-[#666666] mt-1 truncate" />}
              >
                {asset.area}
              </TooltipTrigger>
              <TooltipContent>{asset.area}</TooltipContent>
            </Tooltip>
          )}
        </Link>
      ))}
    </div>
  )
}
