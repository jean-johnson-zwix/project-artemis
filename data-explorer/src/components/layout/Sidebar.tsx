'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { label: 'Detections', icon: AlertCircle, href: '/detections' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed inset-y-0 left-0 w-56 bg-gradient-to-b from-[#151a23] to-[#0f1419] border-r border-[#333333] flex flex-col z-20">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-[#333333]">
        <div className="w-7 h-7 rounded-sm bg-gradient-to-br from-[#00d9ff] to-[#0088ff] flex items-center justify-center text-black font-bold text-sm">
          H
        </div>
        <span className="text-white font-semibold text-sm tracking-[0.5px] uppercase">Hackazona</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ label, icon: Icon, href }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium transition-all duration-150',
                isActive
                  ? 'bg-[#00d9ff]/15 text-[#00d9ff] border border-[#00d9ff]/30 shadow-[0_0_10px_rgba(0,217,255,0.1)]'
                  : 'text-[#999999] hover:text-white hover:bg-[#1f2535]/30 hover:border border-transparent hover:border-[#333333]'
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="px-5 py-4 border-t border-[#333333]">
        <p className="text-xs text-[#666666] uppercase tracking-wider font-semibold">Industrial AI Platform</p>
      </div>
    </aside>
  )
}
