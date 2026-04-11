import AnomalyFeed from '@/components/anomalies/AnomalyFeed'

export default function AnomaliesPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Anomalies</h1>
        <p className="text-slate-400 text-sm mt-1">Threshold breach detection — alarm and trip events</p>
      </div>

      <AnomalyFeed limit={100} />
    </div>
  )
}
