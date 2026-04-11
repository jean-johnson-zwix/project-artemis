'use client'

import { useEffect, useState } from 'react'
import WorkOrderCard from '@/components/maintenance/WorkOrderCard'

interface WorkOrder {
  id: string
  tag: string
  area: string
  workOrderType: string
  priority: string
  status: string
  raisedDate: string
  scheduledDate: string | null
  completedDate: string | null
  assignedTo: string | null
  workDescription: string
  asset: { id: string; name: string; tag: string }
}

const COLUMNS = [
  { key: 'OPEN', label: 'Open', color: 'border-orange-500/40' },
  { key: 'IN_PROGRESS', label: 'In Progress', color: 'border-blue-500/40' },
  { key: 'COMPLETED', label: 'Completed', color: 'border-green-500/40' },
]

export default function MaintenancePage() {
  const [orders, setOrders] = useState<WorkOrder[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/maintenance')
      .then((r) => r.json())
      .then((data) => {
        setOrders(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Maintenance</h1>
        <p className="text-slate-400 text-sm mt-1">Work order kanban board</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-3 gap-4">
          {COLUMNS.map((c) => (
            <div key={c.key} className="space-y-3">
              <div className="h-8 bg-slate-800 animate-pulse rounded" />
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-28 bg-slate-800 animate-pulse rounded-lg" />
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {COLUMNS.map((col) => {
            const colOrders = orders.filter((o) => o.status === col.key)
            return (
              <div key={col.key} className={`rounded-lg border ${col.color} bg-slate-900/50 p-3`}>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-slate-300">{col.label}</h2>
                  <span className="text-xs bg-slate-700 text-slate-400 rounded-full px-2 py-0.5">
                    {colOrders.length}
                  </span>
                </div>
                <div className="space-y-2 max-h-[calc(100vh-200px)] overflow-y-auto">
                  {colOrders.map((wo) => (
                    <WorkOrderCard key={wo.id} wo={wo} />
                  ))}
                  {colOrders.length === 0 && (
                    <p className="text-xs text-slate-600 text-center py-8">No work orders</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
