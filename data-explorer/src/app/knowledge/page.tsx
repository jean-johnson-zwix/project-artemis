import ChatWindow from '@/components/knowledge/ChatWindow'

export default function KnowledgePage() {
  return (
    <div className="p-6">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-white">Knowledge Base</h1>
        <p className="text-slate-400 text-sm mt-1">RAG-powered assistant with access to SOPs, manuals, and maintenance records</p>
      </div>
      <div className="rounded-lg border border-slate-700 bg-slate-900">
        <ChatWindow />
      </div>
    </div>
  )
}
