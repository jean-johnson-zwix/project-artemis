import { cn } from '@/lib/utils'

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  variant?: 'green' | 'yellow' | 'red' | 'blue' | 'default'
}

const variantStyles = {
  green: 'border-[#00ff9f]/30 bg-[#00ff9f]/5 hover:border-[#00ff9f]/50 hover:shadow-[0_0_20px_rgba(0,255,159,0.15)]',
  yellow: 'border-[#ff6b35]/30 bg-[#ff6b35]/5 hover:border-[#ff6b35]/50 hover:shadow-[0_0_20px_rgba(255,107,53,0.15)]',
  red: 'border-[#ff6b35]/30 bg-[#ff6b35]/5 hover:border-[#ff6b35]/50 hover:shadow-[0_0_20px_rgba(255,107,53,0.15)]',
  blue: 'border-[#00d9ff]/30 bg-[#00d9ff]/5 hover:border-[#00d9ff]/50 hover:shadow-[0_0_20px_rgba(0,217,255,0.15)]',
  default: 'border-[#333333] bg-[#1f2535]/30 hover:border-[#00d9ff]/30 hover:shadow-[0_4px_12px_rgba(0,0,0,0.3)]',
}

const valueStyles = {
  green: 'text-[#00ff9f]',
  yellow: 'text-[#ff6b35]',
  red: 'text-[#ff6b35]',
  blue: 'text-[#00d9ff]',
  default: 'text-white',
}

export default function KpiCard({ title, value, subtitle, variant = 'default' }: KpiCardProps) {
  return (
    <div className={cn('rounded-sm border p-5 transition-all duration-150 ease-in-out', variantStyles[variant])}>
      <p className="text-xs font-semibold text-[#999999] uppercase tracking-[0.5px] mb-2">{title}</p>
      <p className={cn('text-3xl font-bold', valueStyles[variant])}>{value}</p>
      {subtitle && <p className="text-xs text-[#666666] mt-1">{subtitle}</p>}
    </div>
  )
}
