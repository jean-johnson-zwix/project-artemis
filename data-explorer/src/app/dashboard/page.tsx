import prisma from '@/lib/prisma'
import KpiCard from '@/components/dashboard/KpiCard'
import AssetStatusGrid from '@/components/dashboard/AssetStatusGrid'
import RecentAnomaliesTable from '@/components/dashboard/RecentAnomaliesTable'

export const dynamic = 'force-dynamic'

export default async function DashboardPage() {
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)

  const [assetStatusCounts, openWoCount, critFailures, productionLoss] = await Promise.all([
    prisma.asset.groupBy({
      by: ['status'],
      _count: { _all: true },
    }),
    prisma.workOrder.count({
      where: { status: { in: ['OPEN', 'IN_PROGRESS'] } },
    }),
    prisma.failureEvent.count({
      where: {
        severity: { in: ['CRITICAL', 'HIGH'] },
        eventTimestamp: { gte: thirtyDaysAgo },
      },
    }),
    prisma.failureEvent.aggregate({
      _sum: { productionLossBbl: true },
    }),
  ])

  const statusMap = Object.fromEntries(
    assetStatusCounts.map((s) => [s.status, s._count._all])
  )

  const totalLoss = productionLoss._sum.productionLossBbl ?? 0

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">Industrial asset monitoring overview</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard
          title="Operating Assets"
          value={statusMap['OPERATING'] ?? 0}
          subtitle="Currently active"
          variant="green"
        />
        <KpiCard
          title="In Maintenance"
          value={statusMap['MAINTENANCE'] ?? 0}
          subtitle="Under maintenance"
          variant="yellow"
        />
        <KpiCard
          title="Open Work Orders"
          value={openWoCount}
          subtitle="Requiring attention"
          variant={openWoCount > 10 ? 'red' : 'blue'}
        />
        <KpiCard
          title="Critical Failures (30d)"
          value={critFailures}
          subtitle={`${totalLoss.toFixed(0)} bbl production loss`}
          variant={critFailures > 0 ? 'red' : 'default'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Asset Status Overview</h2>
          <AssetStatusGrid />
        </div>

        <div className="rounded-lg border border-slate-700 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Recent Anomalies</h2>
          <RecentAnomaliesTable />
        </div>
      </div>
    </div>
  )
}
