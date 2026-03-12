import { useRef, useState } from 'react';
import { api } from '../api/client';
import MarkdownViewer from '../components/MarkdownViewer';
import { copyRichText, downloadAsWord, generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';

export default function DocTemplatePage() {
  const { currentProject } = useAppStore();
  const [formatText, setFormatText] = useState('');
  const [contentText, setContentText] = useState('');
  const [formatAnalysis, setFormatAnalysis] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState<string | null>(null);
  const cancelledRef = useRef(false);

  const handleFormatFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setFormatText(reader.result as string);
    reader.readAsText(file);
  };

  const handleContentFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setContentText(reader.result as string);
    reader.readAsText(file);
  };

  const analyzeFormat = async () => {
    if (!formatText.trim()) return;
    setLoading('analyze');
    cancelledRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'material_summary',
        kwargs: { file_context: formatText, mode: 'format_analysis' },
      });
      const check = async () => {
        if (cancelledRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') { setFormatAnalysis(status.result || ''); setLoading(null); }
        else if (status.status === 'error') { setFormatAnalysis(`오류: ${status.error}`); setLoading(null); }
        else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) {
      setFormatAnalysis(`오류: ${err.message}`);
      setLoading(null);
    }
  };

  const generateDoc = async () => {
    if (!formatAnalysis || !contentText.trim()) return;
    setLoading('generate');
    cancelledRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'material_summary',
        kwargs: {
          file_context: contentText,
          mode: 'apply_format',
          format_spec: formatAnalysis,
        },
      });
      const check = async () => {
        if (cancelledRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') { setResult(status.result || ''); setLoading(null); }
        else if (status.status === 'error') { setResult(`오류: ${status.error}`); setLoading(null); }
        else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) {
      setResult(`오류: ${err.message}`);
      setLoading(null);
    }
  };

  const handleStop = () => {
    cancelledRef.current = true;
    setLoading(null);
  };

  const downloadResult = (ext: string) => {
    const blob = new Blob([result], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = generateFilename('문서양식', ext, currentProject); a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">📋 문서양식 - 포맷 복제기</h1>
      <p className="text-sm text-[#787774] mb-6">기존 문서의 양식을 분석하고 새 콘텐츠에 적용합니다.</p>

      {/* Step 1: Format */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <div className="text-sm font-semibold text-[#37352F] mb-3">Step 1. 양식 문서</div>
        <label className="inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3] mb-3">
          📂 양식 파일 선택
          <input type="file" accept=".txt,.md,.docx" onChange={handleFormatFile} className="hidden" />
        </label>
        <textarea value={formatText} onChange={(e) => setFormatText(e.target.value)}
          placeholder="양식 문서 내용을 붙여넣거나 파일을 업로드하세요..."
          rows={4}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none mb-3" />
        {loading === 'analyze' ? (
          <div className="flex gap-2">
            <span className="px-4 py-2 bg-[#b0b0b0] text-white text-sm rounded-lg">분석 중...</span>
            <button onClick={handleStop}
              className="px-4 py-2 bg-[#EB5757] text-white text-sm rounded-lg hover:bg-[#d94848]">
              중지
            </button>
          </div>
        ) : (
          <button onClick={analyzeFormat} disabled={!formatText.trim()}
            className="px-4 py-2 bg-[#2383E2] text-white text-sm rounded-lg hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0]">
            🔍 양식 분석
          </button>
        )}
        {formatAnalysis && (
          <div className="mt-3 p-3 bg-[#F7F6F3] rounded-lg text-xs max-h-32 overflow-y-auto">
            <MarkdownViewer content={formatAnalysis} />
          </div>
        )}
      </div>

      {/* Step 2: Content */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <div className="text-sm font-semibold text-[#37352F] mb-3">Step 2. 새 콘텐츠</div>
        <label className="inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3] mb-3">
          📂 콘텐츠 파일 선택
          <input type="file" accept=".txt,.md,.docx" onChange={handleContentFile} className="hidden" />
        </label>
        <textarea value={contentText} onChange={(e) => setContentText(e.target.value)}
          placeholder="양식에 맞춰 정리할 콘텐츠를 입력하세요..."
          rows={6}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none" />
      </div>

      {/* Step 3: Generate */}
      {loading === 'generate' ? (
        <div className="flex gap-2 mb-4">
          <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
            생성 중...
          </div>
          <button onClick={handleStop}
            className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
            중지
          </button>
        </div>
      ) : (
        <button onClick={generateDoc} disabled={!formatAnalysis || !contentText.trim()}
          className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
          🤖 양식 적용 문서 생성
        </button>
      )}

      {result && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-[#37352F]">결과</div>
            <div className="flex gap-2">
              <button onClick={() => downloadAsWord(result, generateFilename('문서양식', 'docx', currentProject))} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">📄 Word</button>
              <button onClick={() => downloadResult('md')} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">MD</button>
              <button onClick={() => copyRichText(result)} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">복사</button>
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
