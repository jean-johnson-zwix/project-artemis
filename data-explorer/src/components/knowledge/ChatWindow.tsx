'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const SUGGESTED_QUESTIONS = [
  'What is the startup procedure for V-101?',
  'What are the main failure modes for K-201?',
  'Show me the safety requirements for HP separator',
  'What maintenance intervals are recommended?',
]

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content }
    const assistantId = (Date.now() + 1).toString()

    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: 'assistant', content: '' },
    ])
    setIsLoading(true)

    abortRef.current = new AbortController()

    try {
      const allMessages = [...messages, userMsg]
      const response = await fetch('/api/knowledge/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: allMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) throw new Error(await response.text())

      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let assistantContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        // Parse AI SDK UIMessageStream format
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('0:')) {
            // Text chunk
            try {
              const text = JSON.parse(line.slice(2))
              if (typeof text === 'string') {
                assistantContent += text
                setMessages((prev) =>
                  prev.map((m) => (m.id === assistantId ? { ...m, content: assistantContent } : m))
                )
              }
            } catch {
              // not JSON, skip
            }
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: 'Error: Could not get a response.' } : m
          )
        )
      }
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const val = inputValue.trim()
    if (!val) return
    setInputValue('')
    sendMessage(val)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-100px)]">
      {messages.length === 0 && (
        <div className="p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-200 mb-1">Knowledge Assistant</h2>
            <p className="text-sm text-slate-400">
              Ask questions about equipment, procedures, maintenance intervals, and safety requirements.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => { setInputValue(q) }}
                className="text-xs px-3 py-1.5 rounded-full border border-slate-600 text-slate-400 hover:border-orange-500/50 hover:text-orange-400 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <div key={m.id} className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div
              className={cn(
                'max-w-[80%] rounded-lg px-4 py-3 text-sm',
                m.role === 'user'
                  ? 'bg-orange-500/20 text-orange-100 border border-orange-500/30'
                  : 'bg-slate-800 text-slate-200 border border-slate-700'
              )}
            >
              <div className="whitespace-pre-wrap">
                {m.content}
                {m.role === 'assistant' && !m.content && isLoading && (
                  <span className="inline-flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce inline-block"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-slate-700">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about equipment, procedures, safety..."
            className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-orange-500/50"
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="bg-orange-500 hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  )
}
