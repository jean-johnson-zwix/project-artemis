import prisma from '@/lib/prisma'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'

export const dynamic = 'force-dynamic'

const severityColors: Record<string, string> = {
  CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOW: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

export default async function FailuresPage() {
  const failures = await prisma.failureEvent.findMany({
    include: {
      asset: { select: { id: true, name: true, tag: true } },
      _count: { select: { workOrders: true } },
    },
    orderBy: { eventTimestamp: 'desc' },
  })

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Failure Events</h1>
        <p className="text-slate-400 text-sm mt-1">{failures.length} failure events recorded</p>
      </div>

      <div className="space-y-3">
        {failures.map((f) => (
          <div key={f.id} className="rounded-lg border border-slate-700 bg-slate-900 p-5">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn('text-xs px-1.5 py-0.5 rounded border', severityColors[f.severity] ?? '')}>
                    {f.severity}
                  </span>
                  <span className="text-xs text-slate-500">
                    {format(f.eventTimestamp, 'MMM d, yyyy HH:mm')}
                  </span>
                  {f._count.workOrders > 0 && (
                    <span className="text-xs text-slate-500">
                      · {f._count.workOrders} work order{f._count.workOrders !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <p className="font-medium text-slate-100">{f.failureMode}</p>
                <p className="text-sm text-slate-400">{f.asset.name} · {f.tag} · {f.area}</p>
              </div>
              <div className="text-right flex-shrink-0">
                {f.productionLossBbl != null && (
                  <p className="text-sm font-medium text-red-400">{f.productionLossBbl.toFixed(0)} bbl lost</p>
                )}
                {f.downtimeHours != null && (
                  <p className="text-xs text-slate-500">{f.downtimeHours.toFixed(1)}h downtime</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-xs text-slate-500 mb-1">Root Cause</p>
                <p className="text-slate-300">{f.rootCause}</p>
              </div>
              {f.failureMechanism && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Failure Mechanism</p>
                  <p className="text-slate-300">{f.failureMechanism}</p>
                </div>
              )}
              {f.immediateAction && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Immediate Action</p>
                  <p className="text-slate-300">{f.immediateAction}</p>
                </div>
              )}
              {f.correctiveAction && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Corrective Action</p>
                  <p className="text-slate-300">{f.correctiveAction}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
