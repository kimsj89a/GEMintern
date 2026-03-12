import { useState, useRef, useEffect } from 'react';
import MarkdownViewer from './MarkdownViewer';
import { copyRichText, extractTitle } from '../utils/clipboard';

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
  /** When true, only renders messages area without input. Use with ChatInputBar. */
  externalInput?: boolean;
}

/** Standalone input bar for use outside ChatWidget (e.g. sticky bottom bar) */
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
        <button
          onClick={onStop}
          className="px-4 py-2.5 bg-red-500 text-white text-sm font-semibold rounded-[10px] hover:bg-red-600 transition-all active:scale-[0.97]"
        >
          중지
        </button>
      ) : (
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-4 py-2.5 text-sm font-semibold rounded-[10px] transition-all active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed btn-primary"
        >
          전송
        </button>
      )}
    </div>
  );
}

function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function ChatWidget({ messages, onSend, loading, onStop, placeholder, streamingText, externalInput }: ChatWidgetProps) {
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

  const handleExportSingle = (text: string, _idx: number) => {
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
      {/* Header */}
      {hasAssistantMessages && (
        <div className="flex justify-end mb-2">
          <button
            onClick={handleExportAll}
            className="px-2.5 py-1 text-[11px] font-medium border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-500 transition-colors"
          >
            전체 내보내기
          </button>
        </div>
      )}

      {/* Messages */}
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
                  <MarkdownViewer content={msg.content} />
                </div>
                <div className="flex gap-0.5 mt-1 ml-2">
                  <button
                    onClick={() => handleCopy(msg.content, i)}
                    className="px-2 py-0.5 text-[10px] text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors font-medium"
                  >
                    {copiedIdx === i ? '✓ 복사됨' : '복사'}
                  </button>
                  <button
                    onClick={() => handleExportSingle(msg.content, i)}
                    className="px-2 py-0.5 text-[10px] text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors font-medium"
                  >
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
              <MarkdownViewer content={streamingText} />
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

      {/* Input (hidden when externalInput is used) */}
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
            <button
              onClick={onStop}
              className="px-4 py-2.5 bg-red-500 text-white text-sm font-semibold rounded-[10px] hover:bg-red-600 transition-all active:scale-[0.97]"
            >
              중지
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 text-sm font-semibold rounded-[10px] transition-all active:scale-[0.97] disabled:opacity-40 disabled:cursor-not-allowed btn-primary"
            >
              전송
            </button>
          )}
        </div>
      )}
    </div>
  );
}
