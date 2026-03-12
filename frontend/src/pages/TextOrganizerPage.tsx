import { useRef, useState } from 'react';
import { api } from '../api/client';
import MarkdownViewer from '../components/MarkdownViewer';
import { copyRichText, downloadAsWord, generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';

export default function TextOrganizerPage() {
  const { currentProject } = useAppStore();
  const [text, setText] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const cancelledRef = useRef(false);

  const handleOrganize = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult('');
    cancelledRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'material_summary',
        kwargs: { file_context: text, mode: 'text_organize' },
      });
      const check = async () => {
        if (cancelledRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') { setResult(status.result || ''); setLoading(false); }
        else if (status.status === 'error') { setResult(`오류: ${status.error}`); setLoading(false); }
        else setTimeout(check, 1000);
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
    a.href = url; a.download = generateFilename('문장정리', ext, currentProject); a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">✏️ 문장 정리기</h1>
      <p className="text-sm text-[#787774] mb-6">비정형 텍스트를 깔끔한 불릿포인트로 정리합니다.</p>

      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="정리할 텍스트를 입력하세요..."
          rows={10}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
        />
      </div>

      {loading ? (
        <div className="flex gap-2 mb-4">
          <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
            정리 중...
          </div>
          <button onClick={handleStop}
            className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
            중지
          </button>
        </div>
      ) : (
        <button onClick={handleOrganize} disabled={!text.trim()}
          className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
          ✏️ 정리 실행
        </button>
      )}

      {result && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-[#37352F]">결과</div>
            <div className="flex gap-2">
              <button onClick={() => downloadAsWord(result, generateFilename('문장정리', 'docx', currentProject))} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">📄 Word</button>
              <button onClick={() => downloadResult('txt')} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">TXT</button>
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
