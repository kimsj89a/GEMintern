import { useState, useRef, useEffect } from 'react';
import MarkdownViewer from './MarkdownViewer';

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
}

function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export default function ChatWidget({ messages, onSend, loading, onStop, placeholder, streamingText }: ChatWidgetProps) {
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
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  const handleExportSingle = (text: string, idx: number) => {
    downloadText(text, `answer_${idx + 1}.md`);
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
    <div className="flex flex-col h-full">
      {/* Header with export-all */}
      {hasAssistantMessages && (
        <div className="flex justify-end mb-2">
          <button
            onClick={handleExportAll}
            className="px-2 py-1 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] text-[#787774]"
          >
            전체 내보내기 (.md)
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-3">
        {messages.length === 0 && !streamingText && (
          <div className="text-sm text-[#9B9A97] text-center py-8">
            질문을 입력하세요.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[80%] px-4 py-2 rounded-xl text-sm bg-[#2383E2] text-white whitespace-pre-wrap">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-[85%]">
                <div className="px-4 py-3 rounded-xl bg-[#F7F6F3]">
                  <MarkdownViewer content={msg.content} />
                </div>
                <div className="flex gap-1 mt-1 ml-1">
                  <button
                    onClick={() => handleCopy(msg.content, i)}
                    className="px-2 py-0.5 text-[10px] text-[#9B9A97] hover:text-[#37352F] hover:bg-[#F7F6F3] rounded transition-colors"
                  >
                    {copiedIdx === i ? '복사됨' : '복사'}
                  </button>
                  <button
                    onClick={() => handleExportSingle(msg.content, i)}
                    className="px-2 py-0.5 text-[10px] text-[#9B9A97] hover:text-[#37352F] hover:bg-[#F7F6F3] rounded transition-colors"
                  >
                    내보내기
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[85%] px-4 py-3 rounded-xl bg-[#F7F6F3]">
              <MarkdownViewer content={streamingText} />
              <span className="animate-pulse text-[#2383E2]">|</span>
            </div>
          </div>
        )}
        {loading && !streamingText && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-xl text-sm bg-[#F7F6F3] text-[#9B9A97]">
              답변 생성 중...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder={placeholder || '질문을 입력하세요...'}
          disabled={loading}
          className="flex-1 px-4 py-2.5 border border-[#E9E9E7] rounded-xl text-sm focus:outline-none focus:border-[#2383E2] disabled:bg-[#F7F6F3]"
        />
        {loading && onStop ? (
          <button
            onClick={onStop}
            className="px-4 py-2.5 bg-[#EB5757] text-white text-sm rounded-xl hover:bg-[#d94848] transition-colors"
          >
            중지
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-[#2383E2] text-white text-sm rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors"
          >
            전송
          </button>
        )}
      </div>
    </div>
  );
}
