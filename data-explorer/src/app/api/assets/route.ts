import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const area = searchParams.get('area')
  const status = searchParams.get('status')
  const search = searchParams.get('search')

  const where: Record<string, unknown> = {}
  if (area) where.area = area
  if (status) where.status = status
  if (search) {
    where.OR = [
      { name: { contains: search, mode: 'insensitive' } },
      { tag: { contains: search, mode: 'insensitive' } },
    ]
  }

  const assets = await prisma.asset.findMany({
    where,
    include: {
      _count: { select: { sensors: true } },
    },
    orderBy: [{ area: 'asc' }, { name: 'asc' }],
  })

  return NextResponse.json(assets)
}
