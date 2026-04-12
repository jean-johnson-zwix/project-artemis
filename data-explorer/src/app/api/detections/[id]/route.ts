import { NextRequest, NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params

  const detection = await prisma.detection.findUnique({
    where: { id },
    include: { insight: true },
  })

  if (!detection) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  const insight = detection.insight
    ? {
        what: detection.insight.what,
        why: detection.insight.why,
        evidence: detection.insight.evidence as string[],
        confidence: detection.insight.confidence,
        remainingLifeYears: detection.insight.remainingLifeYears,
        recommendedActions: detection.insight.recommendedActions as string[],
        relevantDocs: (detection.insight.relevantDocs ?? []) as object[],
      }
    : null

  return NextResponse.json({
    id: detection.id,
    detectedAt: detection.detectedAt,
    detectionType: detection.detectionType,
    severity: detection.severity,
    assetId: detection.assetId,
    assetTag: detection.assetTag,
    assetName: detection.assetName,
    area: detection.area,
    resolvedAt: detection.resolvedAt,
    resolvedBy: detection.resolvedBy,
    resolutionNotes: detection.resolutionNotes,
    insight,
  })
}
