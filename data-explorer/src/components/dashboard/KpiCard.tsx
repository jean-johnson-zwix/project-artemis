import { cn } from '@/lib/utils'

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  variant?: 'green' | 'yellow' | 'red' | 'blue' | 'default'
}

const variantStyles = {
  green: 'border-green-500/30 bg-green-500/5',
  yellow: 'border-yellow-500/30 bg-yellow-500/5',
  red: 'border-red-500/30 bg-red-500/5',
  blue: 'border-blue-500/30 bg-blue-500/5',
  default: 'border-slate-700 bg-slate-800/50',
}

const valueStyles = {
  green: 'text-green-400',
  yellow: 'text-yellow-400',
  red: 'text-red-400',
  blue: 'text-blue-400',
  default: 'text-white',
}

export default function KpiCard({ title, value, subtitle, variant = 'default' }: KpiCardProps) {
  return (
    <div className={cn('rounded-lg border p-5', variantStyles[variant])}>
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">{title}</p>
      <p className={cn('text-3xl font-bold', valueStyles[variant])}>{value}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  )
}
