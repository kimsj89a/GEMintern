import { useState, useRef } from 'react';
import { api } from '../api/client';
import MarkdownViewer from './MarkdownViewer';
import { copyRichText, downloadAsWord, downloadAsMd, generateFilename } from '../utils/clipboard';

export default function ContractComparePanel({ projectName, selectedDocs }: {
  projectName: string;
  selectedDocs: string[];
}) {
  const [result, setResult] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const cancelledRef = useRef(false);

  const handleGenerate = async () => {
    if (!projectName || generating) return;
    setGenerating(true);
    setError('');
    setResult('');
    cancelledRef.current = false;

    try {
      const { task_id } = await api.contractCompare(
        projectName,
        selectedDocs.length > 0 ? selectedDocs : undefined,
      );

      const poll = async () => {
        if (cancelledRef.current) { setGenerating(false); return; }
        try {
          const status = await api.getTaskStatus(task_id);
          if (status.status === 'complete') {
            setResult(typeof status.result === 'string' ? status.result : JSON.stringify(status.result));
            setGenerating(false);
          } else if (status.status === 'error') {
            setError(status.error || '비교 분석 실패');
            setGenerating(false);
          } else {
            setTimeout(poll, 2000);
          }
        } catch {
          setTimeout(poll, 3000);
        }
      };
      poll();
    } catch (err: any) {
      setError(err.message);
      setGenerating(false);
    }
  };

  const handleCopy = () => {
    copyRichText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!result && !generating && (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-amber-50 flex items-center justify-center text-3xl">
              ⚖️
            </div>
            <div className="text-center">
              <div className="text-sm font-medium text-slate-600 mb-1">신구조문 비교표</div>
              <div className="text-xs text-slate-400 max-w-sm leading-relaxed">
                텀싯(Termsheet)과 계약서(SSA/SHA)를 비교하여
                조문별 일치 여부, 수치 검증, 리스크 분석 보고서를 생성합니다.
              </div>
              <div className="text-xs text-slate-300 mt-2">
                텀싯 + 계약서 초안 문서가 프로젝트에 업로드되어 있어야 합니다
              </div>
            </div>
            <div className="text-center space-y-2">
              <div className="text-xs text-slate-500">
                {selectedDocs.length > 0
                  ? `${selectedDocs.length}개 문서 선택됨`
                  : '전체 문서 대상'}
              </div>
              <button
                onClick={handleGenerate}
                disabled={!projectName}
                className="px-6 py-2.5 bg-amber-600 text-white text-sm font-medium rounded-xl hover:bg-amber-700 disabled:opacity-30 transition-colors"
              >
                비교 분석 시작
              </button>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 max-w-sm">
                {error}
              </div>
            )}
          </div>
        )}

        {generating && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="w-12 h-12 border-3 border-amber-400 border-t-transparent rounded-full animate-spin" />
            <div className="text-center">
              <div className="text-sm font-medium text-slate-600">계약서 비교 분석 중...</div>
              <div className="text-xs text-slate-400 mt-1">텀싯 ↔ 계약서 조문을 대조하고 있습니다</div>
            </div>
            <button
              onClick={() => { cancelledRef.current = true; setGenerating(false); }}
              className="px-4 py-1.5 text-xs text-red-500 border border-red-200 rounded-lg hover:bg-red-50"
            >
              취소
            </button>
          </div>
        )}

        {result && (
          <>
            {/* Action bar */}
            <div className="flex items-center gap-2 justify-end">
              <button onClick={handleCopy}
                className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                {copied ? '✓ 복사됨' : '복사'}
              </button>
              <button onClick={() => downloadAsMd(result, generateFilename('신구비교', 'md', projectName))}
                className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                MD
              </button>
              <button onClick={() => downloadAsWord(result, generateFilename('신구비교', 'docx', projectName))}
                className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                Word
              </button>
              <button onClick={() => { setResult(''); setError(''); }}
                className="px-3 py-1 text-xs text-slate-400 border border-slate-200 rounded-lg hover:bg-slate-50">
                재분석
              </button>
            </div>

            {/* Result */}
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <MarkdownViewer content={result} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
