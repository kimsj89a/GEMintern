import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Options as GfmOptions } from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { createPortal } from 'react-dom';
import { api } from '../api/client';
import { copyRichText, extractTitle } from '../utils/clipboard';

const gfmOptions: GfmOptions = { singleTilde: false };

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatWidgetProps {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  loading?: boolean;
  onStop?: () => void;
  placeholder?: string;
  streamingText?: string;
  externalInput?: boolean;
  projectName?: string;
}

/** Standalone input bar for use outside ChatWidget */
export function ChatInputBar({ onSend, loading, onStop, placeholder }: {
  onSend: (text: string) => void;
  loading?: boolean;
  onStop?: () => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState('');
  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    onSend(text);
  };
  return (
    <div className="flex gap-2">
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
        placeholder={placeholder || '질문을 입력하세요...'}
        disabled={loading}
        className="flex-1 px-4 py-2.5 text-sm input-ring disabled:bg-slate-50 disabled:text-slate-400"
      />
      {loading && onStop ? (
        <button onClick={onStop} className="px-4 py-2.5 bg-red-500 text-white text-sm font-semibold rounded-[10px] hover:bg-red-600 transition-all active:scale-[0.97]">중지</button>
      ) : (
        <button onClick={handleSend} disabled={loading || !input.trim()} className="px-4 py-2.5 text-sm font-semibold rounded-[10px] transition-all active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed btn-primary">전송</button>
      )}
    </div>
  );
}

// ── Citation types ──

interface ParsedCitation {
  id: number;
  source_doc: string;
  page: number | null;
  detail: string;
}

// ── Parse "**출처**" section from AI response ──

function parseCitationsFromText(text: string): { body: string; citations: ParsedCitation[] } {
  const citations: ParsedCitation[] = [];

  // Find the 출처 section (various possible headers)
  const sourceRegex = /\n\*{0,2}출처\*{0,2}\s*\n/i;
  const match = text.match(sourceRegex);
  if (!match || match.index === undefined) {
    return { body: text, citations };
  }

  const body = text.slice(0, match.index).trimEnd();
  const sourceSection = text.slice(match.index + match[0].length);

  // Parse each line: [1] filename.pdf — p.3
  const lines = sourceSection.split('\n');
  for (const line of lines) {
    const m = line.match(/^\s*\[(\d+)\]\s*(.+)/);
    if (m) {
      const id = parseInt(m[1]);
      const rest = m[2].trim();
      // Try to extract page: "filename — p.3" or "filename (p.3)"
      const pageMatch = rest.match(/[—–-]\s*p\.?\s*(\d+)/i) || rest.match(/\(p\.?\s*(\d+)\)/i);
      const page = pageMatch ? parseInt(pageMatch[1]) : null;
      // Clean doc name
      let docName = rest.replace(/\s*[—–-]\s*p\.?\s*\d+/i, '').replace(/\s*\(p\.?\s*\d+\)/i, '').trim();
      // Remove trailing dots, dashes
      docName = docName.replace(/[—–\-\s.]+$/, '').trim();
      if (!docName.endsWith('.md')) docName = docName;
      citations.push({ id, source_doc: docName, page, detail: rest });
    }
  }

  return { body, citations };
}

// ── Citation Badge ──

function CitBadge({ id, citation, onHover, onLeave, onClick }: {
  id: number;
  citation: ParsedCitation;
  onHover: (c: ParsedCitation, e: React.MouseEvent) => void;
  onLeave: () => void;
  onClick: (c: ParsedCitation) => void;
}) {
  return (
    <sup
      className="inline-flex items-center justify-center min-w-[16px] h-4 px-0.5 text-[9px] font-bold text-blue-600 bg-blue-50 rounded cursor-pointer hover:bg-blue-100 transition-colors mx-0.5"
      onMouseEnter={(e) => onHover(citation, e)}
      onMouseLeave={onLeave}
      onClick={(e) => { e.stopPropagation(); onClick(citation); }}
    >
      {id}
    </sup>
  );
}

// ── Citation Tooltip ──

function CitTooltip({ citation, position }: { citation: ParsedCitation; position: { x: number; y: number } }) {
  // Clamp position to viewport
  const left = Math.min(position.x, window.innerWidth - 300);
  const top = position.y + 8;
  return createPortal(
    <div
      className="fixed z-[9999] w-64 bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs pointer-events-none"
      style={{ left, top }}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-base">📄</span>
        <span className="font-semibold text-slate-700 truncate">{citation.source_doc}</span>
        {citation.page != null && (
          <span className="text-slate-400 shrink-0">p.{citation.page}</span>
        )}
      </div>
      <div className="text-[10px] text-blue-500">클릭하여 원문 확인</div>
    </div>,
    document.body,
  );
}

// ── Citation Preview Modal ──

function CitPreviewModal({ citation, projectName, onClose }: {
  citation: ParsedCitation;
  projectName: string;
  onClose: () => void;
}) {
  const [context, setContext] = useState<{
    context: string;
    context_excerpt_range: [number, number];
    heading?: string;
    position?: number;
    page?: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectName || !citation.source_doc) {
      setLoading(false);
      return;
    }
    // Try fetching citation context from the API
    const docName = citation.source_doc.endsWith('.md') ? citation.source_doc : citation.source_doc + '.md';
    api.getCitationContext(projectName, docName, citation.detail || citation.source_doc)
      .then((data: any) => { if (data?.found) setContext(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [citation, projectName]);

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-[520px] max-h-[75vh] flex flex-col overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <span className="text-lg">📄</span>
            <span className="font-bold text-slate-800">{citation.source_doc}</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-lg">✕</button>
        </div>

        {/* Location bar */}
        <div className="px-5 py-2 bg-slate-50 border-b border-slate-100 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
          {citation.page != null && <span>p.{citation.page}</span>}
          {context?.heading && <span className="flex items-center gap-1"><span>📍</span><span className="font-medium text-slate-600">{context.heading}</span></span>}
          {context?.position != null && <span>문서의 약 {context.position}% 위치</span>}
          {!loading && !context?.heading && citation.page == null && <span className="text-slate-400">[{citation.id}] {citation.detail}</span>}
          {loading && <span className="text-slate-400">위치 검색 중...</span>}
        </div>

        {/* Context body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : context?.context && context.context_excerpt_range ? (
            <div className="text-[13px] text-slate-600 leading-relaxed whitespace-pre-wrap bg-slate-50 rounded-lg p-4 border border-slate-200">
              <span className="text-slate-400">…</span>
              {context.context.slice(0, context.context_excerpt_range[0])}
              <mark className="bg-yellow-200/70 text-slate-800 px-0.5 rounded-sm">
                {context.context.slice(context.context_excerpt_range[0], context.context_excerpt_range[1])}
              </mark>
              {context.context.slice(context.context_excerpt_range[1])}
              <span className="text-slate-400">…</span>
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-slate-700 leading-relaxed">
              <div className="font-medium mb-1">[{citation.id}] {citation.source_doc}</div>
              <div className="text-xs text-slate-500">{citation.detail}</div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-100 flex justify-end">
          <button
            onClick={() => {
              const docName = citation.source_doc.endsWith('.md') ? citation.source_doc : citation.source_doc + '.md';
              api.downloadDoc(projectName, docName);
            }}
            className="px-4 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            파일 다운로드
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

// ── Citation-aware Markdown Renderer ──

function CitationMarkdown({ content, projectName }: { content: string; projectName?: string }) {
  const { body, citations } = parseCitationsFromText(content);
  const [tooltip, setTooltip] = useState<{ citation: ParsedCitation; pos: { x: number; y: number } } | null>(null);
  const [preview, setPreview] = useState<ParsedCitation | null>(null);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleHover = useCallback((c: ParsedCitation, e: React.MouseEvent) => {
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    setTooltip({ citation: c, pos: { x: e.clientX, y: e.clientY } });
  }, []);

  const handleLeave = useCallback(() => {
    hoverTimerRef.current = setTimeout(() => setTooltip(null), 200);
  }, []);

  const handleClick = useCallback((c: ParsedCitation) => {
    setTooltip(null);
    setPreview(c);
  }, []);

  // If no citations found, render plain markdown
  if (citations.length === 0) {
    return <PlainMarkdown content={content} />;
  }

  function injectCitations(children: React.ReactNode): React.ReactNode {
    if (!children) return children;
    if (typeof children === 'string') return splitCitations(children);
    if (Array.isArray(children)) {
      return children.map((child, i) => {
        if (typeof child === 'string') return <span key={i}>{splitCitations(child)}</span>;
        return child;
      });
    }
    return children;
  }

  function splitCitations(text: string): React.ReactNode {
    const parts = text.split(/(\[\d+(?:,\s*\d+)*\])/g);
    return parts.map((part, i) => {
      const m = part.match(/^\[([\d,\s]+)\]$/);
      if (m) {
        const ids = m[1].split(',').map((s) => parseInt(s.trim()));
        return (
          <span key={i}>
            {ids.map((id) => {
              const cit = citations.find((c) => c.id === id);
              if (cit) {
                return <CitBadge key={id} id={id} citation={cit} onHover={handleHover} onLeave={handleLeave} onClick={handleClick} />;
              }
              return <sup key={id} className="text-[9px] text-slate-400">[{id}]</sup>;
            })}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  }

  return (
    <>
      <ReactMarkdown
        remarkPlugins={[[remarkGfm, gfmOptions]]}
        rehypePlugins={[rehypeRaw]}
        components={{
          h1: ({ children }) => <h1 className="text-xl font-bold text-slate-800 mt-6 mb-3 pb-2 border-b border-slate-200">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-bold text-slate-800 mt-5 mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold text-slate-700 mt-4 mb-2">{children}</h3>,
          p: ({ children }) => <p className="text-sm text-slate-700 mb-3 leading-[1.75]">{injectCitations(children)}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1 text-sm text-slate-700">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1 text-sm text-slate-700">{children}</ol>,
          li: ({ children }) => <li className="leading-[1.75]">{injectCitations(children)}</li>,
          strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
          del: ({ children }) => <span>~{children}~</span>,
          td: ({ children }) => <td className="border-b border-slate-100 px-3 py-2 text-slate-700">{injectCitations(children)}</td>,
          th: ({ children }) => <th className="border-b border-slate-200 px-3 py-2.5 text-left font-semibold text-slate-700 text-xs uppercase tracking-wider">{children}</th>,
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm border-collapse">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-slate-50">{children}</thead>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-[3px] border-blue-400 pl-4 my-3 text-sm text-slate-500 italic bg-blue-50/30 py-2 rounded-r-lg">{children}</blockquote>
          ),
          code: ({ children, className: codeClass }) => {
            const isBlock = codeClass?.startsWith('language-');
            if (isBlock) {
              return (
                <pre className="bg-slate-900 rounded-xl p-4 my-3 overflow-x-auto">
                  <code className="text-xs text-slate-200" style={{ fontFamily: 'var(--font-mono)' }}>{children}</code>
                </pre>
              );
            }
            return (
              <code className="bg-slate-100 px-1.5 py-0.5 rounded-md text-xs text-rose-600 font-medium" style={{ fontFamily: 'var(--font-mono)' }}>{children}</code>
            );
          },
          hr: () => <hr className="my-5 border-slate-200" />,
          a: ({ href, children }) => (
            <a href={href} className="text-blue-500 hover:text-blue-600 underline underline-offset-2 decoration-blue-200 hover:decoration-blue-400 transition-colors" target="_blank" rel="noreferrer">{children}</a>
          ),
        }}
      >
        {body}
      </ReactMarkdown>

      {/* Source references footer */}
      {citations.length > 0 && (
        <div className="mt-3 pt-2 border-t border-slate-100">
          <div className="text-[10px] font-medium text-slate-400 mb-1.5">출처</div>
          <div className="flex flex-wrap gap-1.5">
            {citations.map((c) => (
              <button
                key={c.id}
                onClick={() => handleClick(c)}
                className="inline-flex items-center gap-1 px-2 py-1 text-[11px] bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-lg transition-colors text-slate-600 hover:text-blue-700"
              >
                <span className="font-bold text-blue-600">[{c.id}]</span>
                <span className="truncate max-w-[140px]">{c.source_doc}</span>
                {c.page != null && <span className="text-slate-400">p.{c.page}</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {tooltip && <CitTooltip citation={tooltip.citation} position={tooltip.pos} />}
      {preview && projectName && (
        <CitPreviewModal citation={preview} projectName={projectName} onClose={() => setPreview(null)} />
      )}
    </>
  );
}

// ── Plain Markdown (no citations) ──

function PlainMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[[remarkGfm, gfmOptions]]}
      rehypePlugins={[rehypeRaw]}
      components={{
        h1: ({ children }) => <h1 className="text-xl font-bold text-slate-800 mt-6 mb-3 pb-2 border-b border-slate-200">{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-bold text-slate-800 mt-5 mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-base font-semibold text-slate-700 mt-4 mb-2">{children}</h3>,
        p: ({ children }) => <p className="text-sm text-slate-700 mb-3 leading-[1.75]">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1 text-sm text-slate-700">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1 text-sm text-slate-700">{children}</ol>,
        li: ({ children }) => <li className="leading-[1.75]">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
        del: ({ children }) => <span>~{children}~</span>,
        td: ({ children }) => <td className="border-b border-slate-100 px-3 py-2 text-slate-700">{children}</td>,
        th: ({ children }) => <th className="border-b border-slate-200 px-3 py-2.5 text-left font-semibold text-slate-700 text-xs uppercase tracking-wider">{children}</th>,
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-slate-50">{children}</thead>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-[3px] border-blue-400 pl-4 my-3 text-sm text-slate-500 italic bg-blue-50/30 py-2 rounded-r-lg">{children}</blockquote>
        ),
        code: ({ children, className: codeClass }) => {
          const isBlock = codeClass?.startsWith('language-');
          if (isBlock) {
            return (
              <pre className="bg-slate-900 rounded-xl p-4 my-3 overflow-x-auto">
                <code className="text-xs text-slate-200" style={{ fontFamily: 'var(--font-mono)' }}>{children}</code>
              </pre>
            );
          }
          return (
            <code className="bg-slate-100 px-1.5 py-0.5 rounded-md text-xs text-rose-600 font-medium" style={{ fontFamily: 'var(--font-mono)' }}>{children}</code>
          );
        },
        hr: () => <hr className="my-5 border-slate-200" />,
        a: ({ href, children }) => (
          <a href={href} className="text-blue-500 hover:text-blue-600 underline underline-offset-2 decoration-blue-200 hover:decoration-blue-400 transition-colors" target="_blank" rel="noreferrer">{children}</a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

// ── Helpers ──

function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

// ── Main ChatWidget ──

export default function ChatWidget({ messages, onSend, loading, onStop, placeholder, streamingText, externalInput, projectName }: ChatWidgetProps) {
  const [input, setInput] = useState('');
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    onSend(text);
  };

  const handleCopy = (text: string, idx: number) => {
    copyRichText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  const handleExportSingle = (text: string) => {
    const title = extractTitle(text);
    downloadText(text, `${title}.md`);
  };

  const handleExportAll = () => {
    const parts = messages.map((msg) => {
      if (msg.role === 'user') return `**Q:** ${msg.content}`;
      return `**A:**\n\n${msg.content}`;
    });
    downloadText(parts.join('\n\n---\n\n'), 'qa_conversation.md');
  };

  const hasAssistantMessages = messages.some((m) => m.role === 'assistant');

  return (
    <div className={externalInput ? '' : 'flex flex-col h-full'}>
      {hasAssistantMessages && (
        <div className="flex justify-end mb-2">
          <button onClick={handleExportAll} className="px-2.5 py-1 text-[11px] font-medium border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-500 transition-colors">
            전체 내보내기
          </button>
        </div>
      )}

      <div className={externalInput ? 'space-y-3' : 'flex-1 overflow-y-auto space-y-3 mb-3'}>
        {messages.length === 0 && !streamingText && (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <svg className="w-8 h-8 mb-2 opacity-40" viewBox="0 0 24 24" fill="none"><path d="M12 21a9 9 0 1 0-7.5-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>
            <span className="text-sm">{placeholder || '질문을 입력하세요.'}</span>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}>
            {msg.role === 'user' ? (
              <div className="max-w-[80%] px-4 py-2.5 rounded-2xl rounded-br-md text-sm text-white whitespace-pre-wrap"
                style={{ background: 'linear-gradient(135deg, #3b82f6, #2563eb)' }}>
                {msg.content}
              </div>
            ) : (
              <div className="max-w-[85%]">
                <div className="px-4 py-3 rounded-2xl rounded-bl-md bg-slate-50 border border-slate-100">
                  <CitationMarkdown content={msg.content} projectName={projectName} />
                </div>
                <div className="flex gap-0.5 mt-1 ml-2">
                  <button onClick={() => handleCopy(msg.content, i)} className="px-2 py-0.5 text-[10px] text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors font-medium">
                    {copiedIdx === i ? '✓ 복사됨' : '복사'}
                  </button>
                  <button onClick={() => handleExportSingle(msg.content)} className="px-2 py-0.5 text-[10px] text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors font-medium">
                    내보내기
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {streamingText && (
          <div className="flex justify-start animate-fade-in">
            <div className="max-w-[85%] px-4 py-3 rounded-2xl rounded-bl-md bg-slate-50 border border-slate-100">
              <PlainMarkdown content={streamingText} />
              <span className="inline-block w-0.5 h-4 bg-blue-400 animate-pulse ml-0.5 align-text-bottom" />
            </div>
          </div>
        )}
        {loading && !streamingText && (
          <div className="flex justify-start animate-fade-in">
            <div className="px-4 py-3 rounded-2xl rounded-bl-md bg-slate-50 border border-slate-100 flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-slate-400">답변 생성 중</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {!externalInput && (
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder={placeholder || '질문을 입력하세요...'}
            disabled={loading}
            className="flex-1 px-4 py-2.5 text-sm input-ring disabled:bg-slate-50 disabled:text-slate-400"
          />
          {loading && onStop ? (
            <button onClick={onStop} className="px-4 py-2.5 bg-red-500 text-white text-sm font-semibold rounded-[10px] hover:bg-red-600 transition-all active:scale-[0.97]">중지</button>
          ) : (
            <button onClick={handleSend} disabled={loading || !input.trim()} className="px-4 py-2.5 text-sm font-semibold rounded-[10px] transition-all active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed btn-primary">전송</button>
          )}
        </div>
      )}
    </div>
  );
}
