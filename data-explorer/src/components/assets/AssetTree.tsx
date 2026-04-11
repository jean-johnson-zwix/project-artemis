'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ChevronRight, ChevronDown, Factory } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Asset {
  id: string
  tag: string
  name: string
  type: string
  status: string
  criticality: string
  area: string | null
  children?: Asset[]
}

const statusDot: Record<string, string> = {
  OPERATING: 'bg-green-500',
  MAINTENANCE: 'bg-yellow-500',
  STANDBY: 'bg-slate-500',
}

function AssetNode({ asset, depth = 0 }: { asset: Asset; depth?: number }) {
  const [open, setOpen] = useState(depth === 0)
  const hasChildren = asset.children && asset.children.length > 0

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded hover:bg-slate-800 group cursor-pointer',
          depth > 0 && 'ml-4'
        )}
      >
        <button
          onClick={() => setOpen(!open)}
          className="w-4 h-4 flex-shrink-0 text-slate-500"
        >
          {hasChildren ? (
            open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />
          ) : (
            <span className="w-3 h-3 block" />
          )}
        </button>

        <div className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', statusDot[asset.status] ?? 'bg-slate-600')} />

        <Link
          href={`/assets/${encodeURIComponent(asset.id)}`}
          className="flex-1 flex items-center gap-2 min-w-0"
          onClick={(e) => e.stopPropagation()}
        >
          <span className="text-sm text-slate-300 truncate group-hover:text-white">{asset.name}</span>
          <span className="text-xs text-slate-500 flex-shrink-0">{asset.tag}</span>
        </Link>

        <span className="text-xs text-slate-600">{asset.type}</span>
      </div>

      {open && hasChildren && (
        <div>
          {asset.children!.map((child) => (
            <AssetNode key={child.id} asset={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function AssetTree({ assets }: { assets: Asset[] }) {
  // Build hierarchy
  const map = new Map(assets.map((a) => [a.id, { ...a, children: [] as Asset[] }]))
  const roots: Asset[] = []

  for (const asset of map.values()) {
    const raw = assets.find((a) => a.id === asset.id)!
    const parentId = (raw as Asset & { parentId?: string }).parentId
    if (parentId && map.has(parentId)) {
      map.get(parentId)!.children!.push(asset)
    } else {
      roots.push(asset)
    }
  }

  return (
    <div className="space-y-0.5">
      {roots.map((asset) => (
        <AssetNode key={asset.id} asset={asset} />
      ))}
    </div>
  )
}
