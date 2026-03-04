import { useRef, useState } from 'react';
import { api } from '../api/client';

const TONES = [
  { value: 'professional', label: '비즈니스 (합니다체)' },
  { value: 'formal', label: '격식 (합쇼체)' },
  { value: 'casual', label: '캐주얼 (해요체)' },
];

const LANGUAGES = [
  { value: '한국어', label: '한국어' },
  { value: 'English', label: 'English' },
  { value: '日本語', label: '日本語' },
];

export default function QuickMailPage() {
  const [context, setContext] = useState('');
  const [prompt, setPrompt] = useState('');
  const [tone, setTone] = useState('professional');
  const [language, setLanguage] = useState('한국어');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const cancelledRef = useRef(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResult('');
    cancelledRef.current = false;
    try {
      const { task_id } = await api.quickmailGenerate({
        prompt: prompt.trim(),
        context: context.trim(),
        tone,
        language,
      });
      const poll = async () => {
        if (cancelledRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          setResult(status.result || '');
          setLoading(false);
        } else if (status.status === 'error') {
          setResult(`오류: ${status.error}`);
          setLoading(false);
        } else {
          // Show streaming chunks
          if (status.chunks?.length) {
            setResult(status.chunks.join(''));
          }
          setTimeout(poll, 500);
        }
      };
      poll();
    } catch (err: any) {
      setResult(`오류: ${err.message}`);
      setLoading(false);
    }
  };

  const handleStop = () => {
    cancelledRef.current = true;
    setLoading(false);
  };

  const handleCopy = () => {
    if (!result) return;
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 'Enter' && !loading) {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">✉️ QuickMail</h1>
      <p className="text-sm text-[#787774] mb-6">AI 이메일 작성 도우미</p>

      {/* Context (original email) */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <label className="block text-xs font-semibold text-[#787774] uppercase tracking-wider mb-2">
          원본 메일 <span className="font-normal normal-case">(답장 시 붙여넣기, 새 메일이면 비워두기)</span>
        </label>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="답장할 원본 메일 내용을 여기에 붙여넣기"
          rows={3}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm text-[#555] bg-[#f9fafb] focus:outline-none focus:border-[#2383E2] resize-y"
        />

        <label className="block text-xs font-semibold text-[#787774] uppercase tracking-wider mb-2 mt-4">
          요청
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={"예: 일정 확인했고 참석하겠다고 답장\n예: 견적 검토 후 다음 주 미팅 요청\n예: 프로젝트 진행 상황 공유 메일 작성"}
          rows={4}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-y"
        />

        <div className="flex gap-3 mt-3">
          <div className="flex-1">
            <label className="block text-xs font-semibold text-[#787774] uppercase tracking-wider mb-1">톤</label>
            <select value={tone} onChange={(e) => setTone(e.target.value)}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm bg-white focus:outline-none focus:border-[#2383E2]">
              {TONES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-semibold text-[#787774] uppercase tracking-wider mb-1">언어</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm bg-white focus:outline-none focus:border-[#2383E2]">
              {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mb-4">
        {loading ? (
          <>
            <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center animate-pulse">
              생성 중...
            </div>
            <button onClick={handleStop}
              className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
              중지
            </button>
          </>
        ) : (
          <>
            <button onClick={handleGenerate} disabled={!prompt.trim()}
              className="flex-1 py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors">
              ✉️ 생성
            </button>
            <button onClick={handleCopy} disabled={!result}
              className="px-6 py-2.5 bg-[#F1F3F5] text-[#37352F] text-sm font-semibold rounded-xl hover:bg-[#e5e7eb] disabled:opacity-40 transition-colors">
              {copied ? '복사됨!' : '복사'}
            </button>
          </>
        )}
      </div>

      <p className="text-center text-xs text-[#787774] mb-4">
        <kbd className="px-1.5 py-0.5 bg-[#F1F3F5] border border-[#E9E9E7] rounded text-[11px]">Ctrl</kbd>+
        <kbd className="px-1.5 py-0.5 bg-[#F1F3F5] border border-[#E9E9E7] rounded text-[11px]">Enter</kbd> 생성
      </p>

      {/* Output */}
      {result && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold text-[#787774] uppercase tracking-wider">결과</div>
            <button onClick={handleCopy}
              className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3] transition-colors">
              {copied ? '✅ 복사됨' : '📋 복사'}
            </button>
          </div>
          <div className="whitespace-pre-wrap leading-7 text-[15px] p-3 bg-[#f9fafb] rounded-lg border border-[#E9E9E7]">
            {result}
          </div>
        </div>
      )}
    </div>
  );
}
