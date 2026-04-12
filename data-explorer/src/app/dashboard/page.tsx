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
    <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e]">
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-[#999999] text-sm mt-2">Industrial asset monitoring & proactive AI insights</p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
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
            title="Standby Assets"
            value={statusMap['STANDBY'] ?? 0}
            subtitle="On standby"
            variant="blue"
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
            subtitle={`${totalLoss.toFixed(0)} bbl loss`}
            variant={critFailures > 0 ? 'red' : 'default'}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-[6fr_4fr] gap-6">
          {/* Asset Status Panel */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6 hover:border-[#00d9ff]/30 transition-all duration-150">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 border-b border-[#333333] pb-3">Asset Status Overview</h2>
            <AssetStatusGrid />
          </div>

          {/* Recent Anomalies Panel */}
          <div className="rounded-sm border border-[#333333] bg-[#1f2535]/80 backdrop-blur-sm p-6 hover:border-[#ff6b35]/30 transition-all duration-150">
            <h2 className="text-sm font-semibold text-white uppercase tracking-[0.5px] mb-4 border-b border-[#333333] pb-3">Recent Anomalies</h2>
            <RecentAnomaliesTable />
          </div>
        </div>
      </div>
    </div>
  )
}
