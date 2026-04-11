'use client'

import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { format } from 'date-fns'

interface SensorTrendChartProps {
  sensorId: string
  sensorName: string
  unit: string
  normalMin?: number | null
  normalMax?: number | null
  alarmLow?: number | null
  alarmHigh?: number | null
  tripLow?: number | null
  tripHigh?: number | null
}

interface DataPoint {
  timestamp: string
  value: number
}

export default function SensorTrendChart({
  sensorId,
  sensorName,
  unit,
  normalMin,
  normalMax,
  alarmLow,
  alarmHigh,
  tripLow,
  tripHigh,
}: SensorTrendChartProps) {
  const [data, setData] = useState<DataPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/sensors/${encodeURIComponent(sensorId)}/timeseries`)
      .then((r) => r.json())
      .then((d: DataPoint[]) => {
        setData(d)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [sensorId])

  if (loading) return <div className="h-48 bg-slate-800 animate-pulse rounded" />
  if (data.length === 0) return <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No data</div>

  const chartData = data.map((d) => ({
    ...d,
    ts: new Date(d.timestamp).getTime(),
  }))

  const values = data.map((d) => d.value)
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const padding = (maxVal - minVal) * 0.1 || 1
  const yMin = Math.min(minVal - padding, tripLow ?? minVal - padding, alarmLow ?? minVal - padding)
  const yMax = Math.max(maxVal + padding, tripHigh ?? maxVal + padding, alarmHigh ?? maxVal + padding)

  return (
    <div>
      <p className="text-xs text-slate-400 mb-2">{sensorName} ({unit})</p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="ts"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v) => format(new Date(v), 'MM/dd HH:mm')}
            tick={{ fontSize: 9, fill: '#64748b' }}
            minTickGap={60}
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 9, fill: '#64748b' }}
            width={40}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 4 }}
            labelFormatter={(v) => format(new Date(v as number), 'MMM d HH:mm')}
            formatter={(v) => [`${Number(v).toFixed(3)} ${unit}`, sensorName]}
          />

          {/* Normal range - green tint */}
          {normalMin != null && normalMax != null && (
            <ReferenceArea y1={normalMin} y2={normalMax} fill="#22c55e" fillOpacity={0.05} />
          )}

          {/* Alarm range - yellow lines */}
          {alarmHigh != null && (
            <ReferenceLine y={alarmHigh} stroke="#eab308" strokeDasharray="4 2" strokeWidth={1} />
          )}
          {alarmLow != null && (
            <ReferenceLine y={alarmLow} stroke="#eab308" strokeDasharray="4 2" strokeWidth={1} />
          )}

          {/* Trip range - red lines */}
          {tripHigh != null && (
            <ReferenceLine y={tripHigh} stroke="#ef4444" strokeDasharray="4 2" strokeWidth={1} />
          )}
          {tripLow != null && (
            <ReferenceLine y={tripLow} stroke="#ef4444" strokeDasharray="4 2" strokeWidth={1} />
          )}

          <Line
            type="monotone"
            dataKey="value"
            stroke="#f97316"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
