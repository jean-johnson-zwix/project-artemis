'use client'

import { Tooltip as BaseTooltip } from '@base-ui/react'
import { cn } from '@/lib/utils'

function Tooltip({ children }: { children: React.ReactNode }) {
  return <BaseTooltip.Root>{children}</BaseTooltip.Root>
}

function TooltipTrigger({
  children,
  render,
  className,
  ...props
}: React.ComponentProps<typeof BaseTooltip.Trigger>) {
  return (
    <BaseTooltip.Trigger
      render={render}
      className={cn('cursor-default', className)}
      {...props}
    >
      {children}
    </BaseTooltip.Trigger>
  )
}

function TooltipContent({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { children: React.ReactNode }) {
  return (
    <BaseTooltip.Portal>
      <BaseTooltip.Positioner>
        <BaseTooltip.Popup
          className={cn(
            'z-50 max-w-xs rounded-sm border border-[#333333] bg-[#1a1f2e] px-2.5 py-1.5 text-xs text-white shadow-lg',
            'data-[starting-style]:opacity-0 data-[ending-style]:opacity-0 transition-opacity duration-150',
            className
          )}
          {...(props as React.HTMLAttributes<HTMLDivElement>)}
        >
          {children}
        </BaseTooltip.Popup>
      </BaseTooltip.Positioner>
    </BaseTooltip.Portal>
  )
}

export { Tooltip, TooltipTrigger, TooltipContent }
