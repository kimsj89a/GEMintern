/**
 * QuickChatPage — Upload files and chat with AI immediately.
 * StyleSeed design: white cards on #FAFAFA, single accent, Noto Sans KR.
 */
import { useCallback, useRef, useState } from 'react';
import { api } from '../api/client';
import { useAppStore } from '../stores/appStore';
import { useAuthStore } from '../stores/authStore';
import NoteMarkdownViewer from '../components/NoteMarkdownViewer';

interface ChatMsg { role: 'user' | 'assistant'; content: string }
interface UploadedFile { name: string; text: string; size: number }

const TEXT_EXTS = new Set(['txt', 'md', 'csv', 'json', 'xml', 'html']);

export default function QuickChatPage() {
  const backToDashboard = useAppStore(s => s.backToDashboard);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => requestAnimationFrame(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }));

  const handleFiles = useCallback(async (fileList: File[]) => {
    setUploading(true);
    const parsed: UploadedFile[] = [];
    for (const f of fileList) {
      const ext = f.name.split('.').pop()?.toLowerCase() || '';
      if (TEXT_EXTS.has(ext)) {
        parsed.push({ name: f.name, text: await f.text(), size: f.size });
      } else {
        try {
          const formData = new FormData();
          formData.append('files', f);
          const res = await fetch('/api/parse-file', {
            method: 'POST',
            headers: { Authorization: `Bearer ${useAuthStore.getState().token}` },
            body: formData,
          });
          if (res.ok) {
            const data = await res.json();
            const text = Object.values(data.parsed_texts || {})[0] as string || '';
            if (text) parsed.push({ name: f.name, text, size: f.size });
          }
        } catch {}
      }
    }
    setFiles(prev => [...prev, ...parsed]);
    setUploading(false);
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    setInput('');
    setLoading(true);
    scrollToBottom();

    try {
      const fileContext = files.map(f => `[파일: ${f.name}]\n${f.text}`).join('\n\n---\n\n');
      const { task_id } = await api.startAnalysis({ task_type: 'qa_answer', kwargs: { question: input, file_context: fileContext } });

      const poll = async () => {
        try {
          const status = await api.getTaskStatus(task_id);
          if (status.status === 'complete') {
            setMessages(prev => [...prev, { role: 'assistant', content: typeof status.result === 'string' ? status.result : JSON.stringify(status.result) }]);
            setLoading(false); scrollToBottom();
          } else if (status.status === 'error') {
            setMessages(prev => [...prev, { role: 'assistant', content: `오류: ${status.error || '알 수 없는 오류'}` }]);
            setLoading(false);
          } else setTimeout(poll, 1500);
        } catch { setLoading(false); }
      };
      poll();
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '오류가 발생했습니다.' }]);
      setLoading(false);
    }
  }, [input, loading, files]);

  const formatSize = (b: number) => b < 1024 ? `${b}B` : b < 1048576 ? `${(b / 1024).toFixed(1)}K` : `${(b / 1048576).toFixed(1)}M`;

  return (
    <div className="h-screen flex flex-col bg-[#FAFAFA]" style={{ fontFamily: "'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      {/* Header — StyleSeed */}
      <header className="flex items-center gap-3 px-5 py-3 bg-white border-b border-slate-100 shadow-[0_1px_2px_rgba(0,0,0,0.04)] shrink-0">
        <button onClick={backToDashboard} className="text-[#9B9B9B] hover:text-[#3C3C3C] transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <div className="w-8 h-8 rounded-xl bg-indigo-500 flex items-center justify-center text-white text-sm">💬</div>
        <div>
          <div className="text-sm font-bold text-[#2A2A2A]">빠른 채팅</div>
          <div className="text-[10px] text-[#9B9B9B]">파일 업로드 + AI 대화</div>
        </div>
      </header>

      {/* Main — two column: chat left, files right */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {messages.length === 0 && !loading && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-16 h-16 rounded-2xl bg-white border border-slate-100 shadow-[0_2px_8px_rgba(0,0,0,0.05)] flex items-center justify-center text-3xl mx-auto mb-4">💬</div>
                  <div className="text-sm text-[#6A6A6A]">{files.length > 0 ? '업로드한 파일에 대해 질문하세요' : '파일을 올리고 질문해보세요'}</div>
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[75%] rounded-2xl px-5 py-3 text-[14px] leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-500 text-white rounded-br-lg'
                    : 'bg-white border border-slate-100 text-[#2A2A2A] rounded-bl-lg shadow-[0_1px_3px_rgba(0,0,0,0.05)]'
                }`}>
                  {msg.role === 'assistant' ? (
                    <NoteMarkdownViewer content={msg.content} className="leading-relaxed" />
                  ) : msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-lg px-5 py-3 flex items-center gap-1.5 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
                  <div className="w-1.5 h-1.5 bg-[#9B9B9B] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-1.5 h-1.5 bg-[#9B9B9B] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1.5 h-1.5 bg-[#9B9B9B] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input — StyleSeed card */}
          <div className="px-5 py-3 bg-white border-t border-slate-100">
            <div className="flex gap-2">
              <button onClick={() => fileInputRef.current?.click()}
                className="w-10 h-10 shrink-0 flex items-center justify-center rounded-xl border border-slate-200 text-[#7A7A7A] hover:text-indigo-500 hover:border-indigo-200 transition-colors">
                📎
              </button>
              <input value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder={files.length > 0 ? '파일에 대해 질문하세요...' : '메시지를 입력하세요...'}
                disabled={loading}
                className="flex-1 px-4 py-2.5 text-[14px] bg-[#FAFAFA] border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-400 focus:bg-white disabled:opacity-50 transition-colors" />
              <button onClick={handleSend} disabled={loading || !input.trim()}
                className="px-5 py-2.5 bg-indigo-500 text-white text-sm font-medium rounded-xl hover:bg-indigo-600 disabled:opacity-30 transition-colors shrink-0">
                전송
              </button>
            </div>
          </div>
        </div>

        {/* Right sidebar: uploaded files */}
        <div className="hidden md:flex w-56 shrink-0 border-l border-slate-100 bg-white flex-col overflow-hidden">
          <div className="px-4 pt-4 pb-2">
            <div className="text-xs font-bold text-[#9B9B9B] uppercase tracking-wider mb-2">첨부 파일</div>
            <div
              className="border-2 border-dashed border-slate-200 rounded-xl p-3 hover:border-indigo-300 transition-colors cursor-pointer text-center"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('border-indigo-400', 'bg-indigo-50/30'); }}
              onDragLeave={e => { e.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50/30'); }}
              onDrop={e => { e.preventDefault(); e.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50/30'); handleFiles(Array.from(e.dataTransfer.files)); }}
            >
              <input ref={fileInputRef} type="file" multiple className="hidden"
                accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.txt,.md,.csv,.json"
                onChange={e => { if (e.target.files?.length) handleFiles(Array.from(e.target.files)); e.target.value = ''; }} />
              <div className="text-lg mb-0.5">{uploading ? '⏳' : '📎'}</div>
              <div className="text-[10px] text-[#9B9B9B]">{uploading ? '처리 중...' : '클릭 또는 드래그'}</div>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-1.5">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-1.5 px-2.5 py-2 bg-[#FAFAFA] border border-slate-100 rounded-xl text-xs group">
                <span className="text-indigo-500 shrink-0">📄</span>
                <div className="flex-1 min-w-0">
                  <div className="text-[#3C3C3C] truncate">{f.name}</div>
                  <div className="text-[10px] text-[#9B9B9B]">{formatSize(f.size)}</div>
                </div>
                <button onClick={() => setFiles(prev => prev.filter((_, j) => j !== i))}
                  className="text-[#9B9B9B] hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">✕</button>
              </div>
            ))}
            {files.length === 0 && (
              <div className="text-center py-6 text-[10px] text-[#9B9B9B]">파일을 추가하면<br/>여기에 표시됩니다</div>
            )}
          </div>
          <div className="px-4 py-2 border-t border-slate-100">
            <div className="flex items-baseline gap-1">
              <span className="text-lg font-bold text-[#3C3C3C]">{files.length}</span>
              <span className="text-[10px] text-[#9B9B9B]">개 파일</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
