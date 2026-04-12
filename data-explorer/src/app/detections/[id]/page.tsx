'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { format } from 'date-fns'
import Link from 'next/link'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RelevantDoc {
  doc_id: string
  title: string
  doc_type: string
  snippet: string
  tree_path: string | null
}

interface Insight {
  what: string
  why: string
  evidence: string[]
  confidence: string
  remainingLifeYears: number | null
  recommendedActions: string[]
  relevantDocs: RelevantDoc[]
}

interface Detection {
  id: string
  detectedAt: string
  detectionType: string
  severity: string
  assetId: string
  assetTag: string
  assetName: string
  area: string
  resolvedAt: string | null
  resolvedBy: string | null
  resolutionNotes: string | null
  insight: Insight | null
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/30',
  HIGH:     'text-orange-400 bg-orange-500/10 border-orange-500/30',
  MEDIUM:   'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  LOW:      'text-blue-400 bg-blue-500/10 border-blue-500/30',
}

const DOC_TYPE_STYLES: Record<string, string> = {
  INSPECTION_REPORT:  'text-sky-400 bg-sky-500/10 border-sky-500/30',
  MAINTENANCE_RECORD: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  SAFETY_PROCEDURE:   'text-red-400 bg-red-500/10 border-red-500/30',
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DocCard({ doc }: { doc: RelevantDoc }) {
  const [open, setOpen] = useState(false)
  const style = DOC_TYPE_STYLES[doc.doc_type] ?? 'text-[#999999] bg-[#1f2535]/60 border-[#444444]'

  return (
    <div className="border border-[#2a2a3a] rounded-sm bg-[#161b27]">
      <div className="p-4">
        <p className="text-white text-sm font-semibold mb-0.5">{doc.title}</p>
        <p className="text-[#555555] text-xs mb-3">Document ID: {doc.doc_id}</p>
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-[#999999] hover:text-white transition-colors"
        >
          <span className="text-[10px]">{open ? '▾' : '▸'}</span>
          {open ? 'Hide' : 'Show'} relevance
        </button>
      </div>

      {open && (
        <div className="border-t border-[#2a2a3a] px-4 pb-4 pt-3 space-y-3">
          <div>
            <span className={`text-[10px] px-2 py-0.5 rounded-sm border font-bold tracking-wider uppercase ${style}`}>
              {doc.doc_type.replace(/_/g, ' ')}
            </span>
          </div>
          {doc.snippet && (
            <p className="text-[#aaaaaa] text-xs leading-relaxed border-l-2 border-[#333333] pl-3 italic whitespace-pre-line">
              {doc.snippet}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DetectionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const [detection, setDetection] = useState<Detection | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [resolvedBy, setResolvedBy] = useState('operator')
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [resolving, setResolving] = useState(false)

  useEffect(() => {
    fetch(`/api/detections/${id}`)
      .then((r) => {
        if (r.status === 404) { setNotFound(true); return null }
        return r.json()
      })
      .then((data) => {
        if (data) setDetection(data as Detection)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [id])

  async function handleResolve() {
    if (!detection) return
    setResolving(true)
    try {
      const res = await fetch(`/api/detections/${id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved_by: resolvedBy, resolution_notes: resolutionNotes || null }),
      })
      if (res.ok) {
        setDetection((d) => d ? { ...d, resolvedAt: new Date().toISOString(), resolvedBy } : d)
      }
    } finally {
      setResolving(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e] p-8">
        <div className="space-y-4 max-w-5xl">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-[#1f2535]/50 animate-pulse rounded-sm" />
          ))}
        </div>
      </div>
    )
  }

  if (notFound || !detection) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e] p-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#999999] text-lg mb-4">Detection not found.</p>
          <Link href="/detections" className="text-[#00d9ff] hover:underline text-sm">← Back to Detections</Link>
        </div>
      </div>
    )
  }

  const insight = detection.insight
  const relevantDocs: RelevantDoc[] = Array.isArray(insight?.relevantDocs) ? insight.relevantDocs : []
  const isResolved = !!detection.resolvedAt

  const detectedStr = format(new Date(detection.detectedAt), 'yyyy-MM-dd HH:mm') + ' UTC'

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f1419] to-[#1a1f2e]">
      <div className="p-6 max-w-6xl mx-auto">

        {/* Back */}
        <Link href="/detections" className="text-xs text-[#999999] hover:text-white uppercase tracking-wider mb-5 inline-block">
          ← Back to Detections
        </Link>

        {/* Header row */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-xs text-[#999999] mb-1">
              Asset: {detection.assetTag} | {detection.assetName}
            </p>
            <h1 className="text-2xl font-bold text-white tracking-tight mb-3">Alert Details</h1>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs px-2.5 py-1 rounded-sm border font-bold tracking-wider ${SEVERITY_STYLES[detection.severity] ?? ''}`}>
                {detection.severity}
              </span>
              <span className="text-xs px-2.5 py-1 rounded-sm border border-[#444444] text-[#999999] font-bold tracking-wider uppercase">
                {detection.detectionType.replace(/_/g, ' ')}
              </span>
              {isResolved ? (
                <span className="text-xs px-2.5 py-1 rounded-sm border border-green-500/30 text-green-400 bg-green-500/10 font-bold tracking-wider">
                  RESOLVED
                </span>
              ) : (
                <span className="text-xs px-2.5 py-1 rounded-sm border border-[#ff6b35]/30 text-[#ff6b35] bg-[#ff6b35]/10 font-bold tracking-wider">
                  OPEN
                </span>
              )}
            </div>
          </div>
          <div className="text-right text-xs text-[#666666] mt-1">
            <p>Detected: {detectedStr}</p>
            {isResolved && detection.resolvedBy && (
              <p className="mt-1 text-green-400">Resolved by {detection.resolvedBy}</p>
            )}
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left column — 2/3 */}
          <div className="lg:col-span-2 space-y-6">

            {/* Executive Summary */}
            <section>
              <h2 className="text-base font-bold text-white mb-3">Executive Summary</h2>
              {insight ? (
                <div className="space-y-2">
                  <p className="text-sm text-[#cccccc]">
                    <span className="text-white font-semibold">Summary:</span> {insight.what}
                  </p>
                  <p className="text-sm text-[#cccccc]">
                    <span className="text-white font-semibold">Likely cause:</span> {insight.why}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-[#555555] italic">AI analysis in progress…</p>
              )}
            </section>

            {/* Supporting Evidence */}
            {insight && insight.evidence.length > 0 && (
              <section>
                <h2 className="text-base font-bold text-white mb-3">Supporting Evidence</h2>
                <ul className="space-y-1.5">
                  {insight.evidence.map((e, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-[#cccccc]">
                      <span className="text-[#555555] mt-0.5 shrink-0">•</span>
                      <span>{e}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Relevant Documents */}
            {relevantDocs.length > 0 && (
              <section>
                <h2 className="text-base font-bold text-white mb-3">Relevant Documents</h2>
                <div className="space-y-3">
                  {relevantDocs.map((doc, i) => (
                    <DocCard key={doc.doc_id ?? i} doc={doc} />
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* Right column — 1/3 */}
          <div className="space-y-6">

            {/* Recommended Response */}
            {insight && insight.recommendedActions.length > 0 && (
              <section>
                <h2 className="text-base font-bold text-white mb-3">Recommended Response</h2>
                <ul className="space-y-1.5">
                  {insight.recommendedActions.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-[#cccccc]">
                      <span className="text-[#555555] mt-0.5 shrink-0">•</span>
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Resolve form */}
            {!isResolved && (
              <section className="border border-[#333333] rounded-sm bg-[#1f2535]/60 p-4 space-y-4">
                <div>
                  <label className="block text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1.5">
                    Resolved by
                  </label>
                  <input
                    type="text"
                    value={resolvedBy}
                    onChange={(e) => setResolvedBy(e.target.value)}
                    className="w-full bg-[#0f1419] border border-[#333333] rounded-sm px-3 py-2 text-white text-sm placeholder-[#555555] focus:outline-none focus:border-[#555555]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#999999] uppercase tracking-wider font-semibold mb-1.5">
                    How was it resolved?
                  </label>
                  <textarea
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    rows={3}
                    placeholder="e.g. Replaced corroded section, coating reapplied, sensor recalibrated…"
                    className="w-full bg-[#0f1419] border border-[#333333] rounded-sm px-3 py-2 text-white text-sm placeholder-[#555555] focus:outline-none focus:border-[#555555] resize-none"
                  />
                </div>
                <button
                  onClick={handleResolve}
                  disabled={resolving || !resolvedBy.trim()}
                  className="w-full py-2.5 rounded-sm text-sm font-semibold tracking-wide bg-[#2a7a5a] hover:bg-[#30906a] disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
                >
                  {resolving ? 'Marking as resolved…' : 'Mark as resolved'}
                </button>
              </section>
            )}

            {isResolved && detection.resolutionNotes && (
              <section className="border border-green-500/20 rounded-sm bg-green-500/5 p-4">
                <p className="text-xs text-[#999999] uppercase tracking-wider font-semibold mb-2">Resolution Notes</p>
                <p className="text-sm text-[#cccccc]">{detection.resolutionNotes}</p>
              </section>
            )}

            {/* Asset link */}
            <Link
              href={`/assets/${detection.assetId}`}
              className="block text-center text-xs text-[#00d9ff] hover:underline py-2"
            >
              View Asset: {detection.assetName} →
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
