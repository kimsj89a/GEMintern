/**
 * QuickChatPage — Upload files and chat with AI immediately.
 * No project needed. Files are parsed client-side (text) or sent as inline_docs.
 */
import { useCallback, useRef, useState } from 'react';
import { api } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import NoteMarkdownViewer from '../components/NoteMarkdownViewer';

interface ChatMsg { role: 'user' | 'assistant'; content: string }
interface UploadedFile { name: string; text: string; size: number }

const TEXT_EXTS = new Set(['txt', 'md', 'csv', 'json', 'xml', 'html']);

export default function QuickChatPage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => requestAnimationFrame(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }));

  // ── File upload + parse ──
  const handleFiles = useCallback(async (fileList: File[]) => {
    setUploading(true);
    const parsed: UploadedFile[] = [];
    for (const f of fileList) {
      const ext = f.name.split('.').pop()?.toLowerCase() || '';
      if (TEXT_EXTS.has(ext)) {
        // Read text directly
        const text = await f.text();
        parsed.push({ name: f.name, text, size: f.size });
      } else {
        // Binary files (pdf, docx, xlsx) — upload to server for parsing
        try {
          const formData = new FormData();
          formData.append('files', f);
          // Use a temp project for parsing, or just parse inline
          const res = await fetch('/api/parse-file', {
            method: 'POST',
            headers: { Authorization: `Bearer ${useAuthStore.getState().token}` },
            body: formData,
          });
          if (res.ok) {
            const data = await res.json();
            const texts = data.parsed_texts || {};
            const text = Object.values(texts)[0] as string || '';
            if (text) parsed.push({ name: f.name, text, size: f.size });
          }
        } catch {}
      }
    }
    setFiles(prev => [...prev, ...parsed]);
    setUploading(false);
  }, []);

  // ── Send message ──
  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg: ChatMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    scrollToBottom();

    try {
      // Build inline context from uploaded files
      const fileContext = files.map(f => `[파일: ${f.name}]\n${f.text}`).join('\n\n---\n\n');

      const { task_id } = await api.startAnalysis({
        task_type: 'qa_answer',
        kwargs: {
          question: input,
          file_context: fileContext,
        },
      });

      // Poll for result
      const poll = async () => {
        try {
          const status = await api.getTaskStatus(task_id);
          if (status.status === 'complete') {
            const answer = typeof status.result === 'string' ? status.result : JSON.stringify(status.result);
            setMessages(prev => [...prev, { role: 'assistant', content: answer }]);
            setLoading(false);
            scrollToBottom();
          } else if (status.status === 'error') {
            setMessages(prev => [...prev, { role: 'assistant', content: `오류: ${status.error || '알 수 없는 오류'}` }]);
            setLoading(false);
          } else {
            setTimeout(poll, 1500);
          }
        } catch {
          setLoading(false);
        }
      };
      poll();
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '오류가 발생했습니다.' }]);
      setLoading(false);
    }
  }, [input, loading, files]);

  const formatSize = (bytes: number) => bytes < 1024 ? `${bytes}B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(1)}K` : `${(bytes / 1048576).toFixed(1)}M`;

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      {/* Header */}
      <div className="px-6 pt-5 pb-3">
        <h1 className="text-xl font-bold text-slate-800">💬 빠른 채팅</h1>
        <p className="text-sm text-slate-400 mt-0.5">파일을 업로드하고 바로 AI와 대화하세요</p>
      </div>

      {/* File upload area */}
      <div className="px-6 pb-3">
        <div
          className="border-2 border-dashed border-slate-200 rounded-xl p-4 hover:border-indigo-300 transition-colors cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('border-indigo-400', 'bg-indigo-50/50'); }}
          onDragLeave={e => { e.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50/50'); }}
          onDrop={e => { e.preventDefault(); e.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50/50'); handleFiles(Array.from(e.dataTransfer.files)); }}
        >
          <input ref={fileInputRef} type="file" multiple className="hidden"
            accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.txt,.md,.csv,.json"
            onChange={e => { if (e.target.files?.length) handleFiles(Array.from(e.target.files)); e.target.value = ''; }} />
          {files.length === 0 ? (
            <div className="text-center py-2">
              <div className="text-2xl mb-1">📎</div>
              <div className="text-sm text-slate-500">{uploading ? '파일 처리 중...' : '파일을 드래그하거나 클릭하여 업로드'}</div>
              <div className="text-[10px] text-slate-400 mt-1">PDF, Word, Excel, TXT, MD 지원</div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {files.map((f, i) => (
                <div key={i} className="flex items-center gap-1.5 px-2 py-1 bg-indigo-50 border border-indigo-200 rounded-lg text-xs">
                  <span className="text-indigo-600">📄</span>
                  <span className="text-slate-700 max-w-[120px] truncate">{f.name}</span>
                  <span className="text-slate-400">{formatSize(f.size)}</span>
                  <button onClick={e => { e.stopPropagation(); setFiles(prev => prev.filter((_, j) => j !== i)); }}
                    className="text-slate-400 hover:text-red-500 ml-0.5">✕</button>
                </div>
              ))}
              <div className="flex items-center text-[10px] text-slate-400">+ 더 추가</div>
            </div>
          )}
        </div>
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto px-6 space-y-4">
        {messages.length === 0 && !loading && (
          <div className="flex items-center justify-center h-full text-slate-300">
            <div className="text-center">
              <div className="text-4xl mb-2">💬</div>
              <div className="text-sm">{files.length > 0 ? '업로드한 파일에 대해 질문하세요' : '파일을 올리고 질문해보세요'}</div>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed ${
              msg.role === 'user'
                ? 'bg-indigo-500 text-white rounded-br-md'
                : 'bg-slate-100 text-slate-800 rounded-bl-md'
            }`}>
              {msg.role === 'assistant' ? (
                <NoteMarkdownViewer content={msg.content} className="leading-relaxed" />
              ) : msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-3 border-t border-slate-100">
        <div className="flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder={files.length > 0 ? '파일에 대해 질문하세요...' : '메시지를 입력하세요...'}
            disabled={loading}
            className="flex-1 px-4 py-2.5 text-[14px] border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-400 disabled:opacity-50" />
          <button onClick={handleSend} disabled={loading || !input.trim()}
            className="px-5 py-2.5 bg-indigo-500 text-white text-sm font-medium rounded-xl hover:bg-indigo-600 disabled:opacity-30 transition-colors">
            전송
          </button>
        </div>
      </div>
    </div>
  );
}
