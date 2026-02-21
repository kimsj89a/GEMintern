import { useRef, useState } from 'react';
import { api } from '../api/client';
import MarkdownViewer from '../components/MarkdownViewer';

const MODES = [
  { id: 'meeting', label: '회의록 정리' },
  { id: 'summary', label: '핵심 요약' },
  { id: 'qa', label: 'Q&A 형식' },
  { id: 'presentation', label: '발표용 정리' },
  { id: 'cleanup', label: '단순 정리' },
];

export default function AudioPage() {
  const [inputMode, setInputMode] = useState<'file' | 'direct'>('direct');
  const [text, setText] = useState('');
  const [processMode, setProcessMode] = useState('meeting');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const cancelledRef = useRef(false);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(reader.result as string);
    reader.readAsText(file);
  };

  const handleProcess = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult('');
    cancelledRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'material_summary',
        kwargs: {
          file_context: text,
          mode: processMode,
        },
      });
      const check = async () => {
        if (cancelledRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          setResult(status.result || '');
          setLoading(false);
        } else if (status.status === 'error') {
          setResult(`오류: ${status.error}`);
          setLoading(false);
        } else {
          setTimeout(check, 1000);
        }
      };
      check();
    } catch (err: any) {
      setResult(`오류: ${err.message}`);
      setLoading(false);
    }
  };

  const handleStop = () => {
    cancelledRef.current = true;
    setLoading(false);
  };

  const downloadResult = (ext: string) => {
    const blob = new Blob([result], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audio_processed.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">🎤 오디오 전사 후처리</h1>
      <p className="text-sm text-[#787774] mb-6">전사된 텍스트를 AI로 정리합니다.</p>

      {/* Input mode */}
      <div className="flex gap-2 mb-4">
        <button onClick={() => setInputMode('direct')}
          className={`px-3 py-1.5 text-sm rounded-lg ${inputMode === 'direct' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          직접 입력
        </button>
        <button onClick={() => setInputMode('file')}
          className={`px-3 py-1.5 text-sm rounded-lg ${inputMode === 'file' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          파일 업로드
        </button>
      </div>

      {/* Input */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        {inputMode === 'file' && (
          <label className="inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3] mb-3">
            📂 텍스트 파일 선택
            <input type="file" accept=".txt,.md" onChange={handleFileUpload} className="hidden" />
          </label>
        )}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="전사된 텍스트를 붙여넣으세요..."
          rows={8}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
        />
      </div>

      {/* Mode selection */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <label className="block text-sm font-medium text-[#37352F] mb-2">처리 모드</label>
        <div className="flex flex-wrap gap-2">
          {MODES.map((m) => (
            <button key={m.id} onClick={() => setProcessMode(m.id)}
              className={`px-3 py-1.5 text-xs rounded-lg border ${processMode === m.id ? 'border-[#2383E2] bg-[#E8F3FC] text-[#2383E2]' : 'border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex gap-2 mb-4">
          <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
            처리 중...
          </div>
          <button onClick={handleStop}
            className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
            중지
          </button>
        </div>
      ) : (
        <button onClick={handleProcess} disabled={!text.trim()}
          className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
          🤖 AI 후처리 실행
        </button>
      )}

      {/* Result */}
      {result && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-[#37352F]">결과</div>
            <div className="flex gap-2">
              <button onClick={() => downloadResult('txt')} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">TXT</button>
              <button onClick={() => downloadResult('md')} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">MD</button>
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto">
            <MarkdownViewer content={result} />
          </div>
        </div>
      )}
    </div>
  );
}
