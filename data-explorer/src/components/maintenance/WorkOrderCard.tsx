import { cn } from '@/lib/utils'
import { format } from 'date-fns'

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

const priorityColors: Record<string, string> = {
  EMERGENCY: 'bg-red-500/20 text-red-400 border-red-500/30',
  CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOW: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

const typeColors: Record<string, string> = {
  EMERGENCY: 'bg-red-500/20 text-red-400 border-red-500/30',
  CORRECTIVE: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  PREVENTIVE: 'bg-green-500/20 text-green-400 border-green-500/30',
  INSPECTION: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  MODIFICATION: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
}

export default function WorkOrderCard({ wo }: { wo: WorkOrder }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-slate-500 font-mono">{wo.id}</p>
        <div className="flex gap-1">
          <span className={cn('text-xs px-1.5 py-0.5 rounded border', priorityColors[wo.priority] ?? '')}>
            {wo.priority}
          </span>
          <span className={cn('text-xs px-1.5 py-0.5 rounded border', typeColors[wo.workOrderType] ?? '')}>
            {wo.workOrderType}
          </span>
        </div>
      </div>
      <p className="text-sm text-slate-200 line-clamp-2">{wo.workDescription}</p>
      <div className="space-y-1">
        <p className="text-xs text-slate-400">{wo.asset.name} · {wo.area}</p>
        {wo.assignedTo && <p className="text-xs text-slate-500">Assigned: {wo.assignedTo}</p>}
        <p className="text-xs text-slate-500">
          Raised: {format(new Date(wo.raisedDate), 'MMM d, yyyy')}
          {wo.scheduledDate && ` · Sched: ${format(new Date(wo.scheduledDate), 'MMM d')}`}
        </p>
      </div>
    </div>
  )
}
