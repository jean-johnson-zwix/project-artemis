import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const status = searchParams.get('status')
  const priority = searchParams.get('priority')
  const area = searchParams.get('area')
  const type = searchParams.get('type')

  const where: Record<string, unknown> = {}
  if (status) where.status = status
  if (priority) where.priority = priority
  if (area) where.area = area
  if (type) where.workOrderType = type

  const workOrders = await prisma.workOrder.findMany({
    where,
    include: {
      asset: { select: { id: true, name: true, tag: true } },
    },
    orderBy: { raisedDate: 'desc' },
  })

  return NextResponse.json(workOrders)
}
