'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Factory,
  AlertTriangle,
  Wrench,
  Flame,
  BookOpen,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { label: 'Assets', icon: Factory, href: '/assets' },
  { label: 'Anomalies', icon: AlertTriangle, href: '/anomalies' },
  { label: 'Maintenance', icon: Wrench, href: '/maintenance' },
  { label: 'Failures', icon: Flame, href: '/failures' },
  { label: 'Knowledge', icon: BookOpen, href: '/knowledge' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed inset-y-0 left-0 w-56 bg-slate-900 border-r border-slate-700 flex flex-col z-20">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-700">
        <div className="w-7 h-7 rounded bg-orange-500 flex items-center justify-center text-white font-bold text-sm">
          H
        </div>
        <span className="text-white font-semibold text-sm tracking-wide">Hackazona</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ label, icon: Icon, href }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="px-5 py-4 border-t border-slate-700">
        <p className="text-xs text-slate-500">Industrial AI Platform</p>
      </div>
    </aside>
  )
}
