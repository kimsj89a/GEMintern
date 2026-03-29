import { useCallback, useRef, useState } from 'react';
import { api } from '../api/client';
import MarkdownViewer from './MarkdownViewer';
import { copyRichText, downloadAsWord, generateFilename } from '../utils/clipboard';

const PRESETS = [
  {
    id: 'quick',
    label: 'Quick Review',
    desc: '5p 미만, 제공 자료 퀵 리뷰',
    icon: '⚡',
    template: 'simple_review',
    mode: 'single',
  },
  {
    id: 'preliminary',
    label: '예비검토',
    desc: '~20p, 상세 예비검토보고서',
    icon: '📋',
    template: 'simple_review',
    mode: 'chained',
  },
  {
    id: 'investment',
    label: '투자심사보고서',
    desc: '실사 제외, 내부 투심용',
    icon: '💰',
    template: 'investment',
    mode: 'chained',
  },
];

export default function ReportPanel({ projectName, selectedDocs }: {
  projectName: string;
  selectedDocs: string[];
}) {
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [additionalContext, setAdditionalContext] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleGenerate = useCallback(async () => {
    const preset = PRESETS.find(p => p.id === selectedPreset);
    if (!preset || !projectName) return;

    setGenerating(true);
    setError('');
    setResult('');

    try {
      const { task_id } = await api.startGenerate({
        project_name: projectName,
        template_option: preset.template,
        mode: preset.mode,
        inputs: {
          template_option: preset.template,
          selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
          context_text: additionalContext || undefined,
        },
      });

      const poll = async () => {
        try {
          const status = await api.getTaskStatus(task_id);
          if (status.status === 'complete') {
            const text = typeof status.result === 'string'
              ? status.result
              : status.result?.text || status.result?.result || JSON.stringify(status.result);
            setResult(text);
            setGenerating(false);
          } else if (status.status === 'error') {
            setError(status.error || '생성 오류');
            setGenerating(false);
          } else {
            pollRef.current = setTimeout(poll, 2500);
          }
        } catch {
          setError('폴링 오류');
          setGenerating(false);
        }
      };
      poll();
    } catch (e: any) {
      setError(e.message);
      setGenerating(false);
    }
  }, [projectName, selectedPreset, selectedDocs, additionalContext]);

  const handleCopy = () => { if (result) copyRichText(result); };
  const handleDownloadWord = () => {
    if (result) downloadAsWord(result, generateFilename('보고서', 'doc', projectName));
  };

  // Config screen
  if (!result && !generating) {
    return (
      <div className="h-full overflow-y-auto p-5 space-y-5">
        {/* Preset selection */}
        <div>
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">보고서 유형</div>
          <div className="grid grid-cols-3 gap-3">
            {PRESETS.map(p => {
              const isSelected = selectedPreset === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedPreset(p.id)}
                  className={`relative p-4 rounded-xl border-2 text-left transition-all ${
                    isSelected
                      ? 'border-blue-500 bg-blue-50/50 shadow-sm'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>
                    </div>
                  )}
                  <span className="text-2xl block mb-2">{p.icon}</span>
                  <div className="text-sm font-medium text-slate-800">{p.label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{p.desc}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Additional context */}
        <div>
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">추가 지시사항 (선택)</div>
          <textarea
            value={additionalContext}
            onChange={e => setAdditionalContext(e.target.value)}
            placeholder="특별히 강조할 내용, 포함/제외 사항 등..."
            className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:border-blue-400 resize-none"
            rows={3}
          />
        </div>

        {/* Doc count info */}
        <div className="text-xs text-slate-400">
          {selectedDocs.length > 0
            ? `선택된 문서 ${selectedDocs.length}개 기반으로 생성`
            : '전체 프로젝트 문서 기반으로 생성'}
        </div>

        {/* Generate button */}
        {error && <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>}
        <button
          onClick={handleGenerate}
          disabled={!selectedPreset}
          className="w-full py-3 text-sm font-medium bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          보고서 생성
        </button>
      </div>
    );
  }

  // Generating
  if (generating) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-400">
        <div className="w-8 h-8 border-3 border-blue-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">보고서 생성 중...</span>
        <span className="text-xs text-slate-300">{PRESETS.find(p => p.id === selectedPreset)?.label}</span>
      </div>
    );
  }

  // Result
  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="px-4 py-2 flex items-center gap-2 border-b border-slate-100 shrink-0">
        <button
          onClick={() => setResult('')}
          className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-100"
        >
          ← 돌아가기
        </button>
        <span className="text-xs text-slate-400 ml-auto">
          {PRESETS.find(p => p.id === selectedPreset)?.label}
        </span>
        <button onClick={handleCopy}
          className="text-xs text-slate-500 hover:text-blue-600 px-2 py-1 rounded hover:bg-blue-50">
          복사
        </button>
        <button onClick={handleDownloadWord}
          className="text-xs text-slate-500 hover:text-blue-600 px-2 py-1 rounded hover:bg-blue-50">
          Word
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <MarkdownViewer content={result} />
      </div>
    </div>
  );
}
