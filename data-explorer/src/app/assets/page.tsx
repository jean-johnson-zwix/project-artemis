import prisma from '@/lib/prisma'
import AssetTree from '@/components/assets/AssetTree'

export const dynamic = 'force-dynamic'

export default async function AssetsPage() {
  const assets = await prisma.asset.findMany({
    orderBy: [{ area: 'asc' }, { name: 'asc' }],
  })

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Assets</h1>
        <p className="text-slate-400 text-sm mt-1">{assets.length} assets across all areas</p>
      </div>

      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
        <AssetTree assets={assets as Parameters<typeof AssetTree>[0]['assets']} />
      </div>
    </div>
  )
}
