import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET() {
  const failures = await prisma.failureEvent.findMany({
    include: {
      asset: { select: { id: true, name: true, tag: true } },
      _count: { select: { workOrders: true } },
    },
    orderBy: { eventTimestamp: 'desc' },
  })

  return NextResponse.json(failures)
}
