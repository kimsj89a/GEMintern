import { useState, useRef, useCallback } from 'react';
import { api } from '../api/client';
import MarkdownViewer from './MarkdownViewer';
import { copyRichText, downloadAsWord, downloadAsMd, generateFilename } from '../utils/clipboard';

interface AnalysisEntry {
  filename: string;
  result: string;
  status: 'pending' | 'generating' | 'done';
}

export default function DocAnalysisPanel({ projectName, selectedDocs }: {
  projectName: string;
  selectedDocs: string[];
}) {
  const [entries, setEntries] = useState<AnalysisEntry[]>([]);
  const [generating, setGenerating] = useState(false);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const cancelledRef = useRef(false);

  const handleGenerate = useCallback(async () => {
    if (!projectName || generating) return;
    const docs = selectedDocs.length > 0 ? selectedDocs : [];
    if (docs.length === 0) return;

    cancelledRef.current = false;
    setGenerating(true);

    // Initialize entries
    const initial: AnalysisEntry[] = docs.map(d => ({
      filename: d.replace('.md', ''),
      result: '',
      status: 'pending',
    }));
    setEntries(initial);
    setExpandedIdx(null);

    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'material_summary_batch',
        project_name: projectName,
        kwargs: {
          project_name: projectName,
          selected_docs: docs,
        },
      });

      // Poll with batch progress
      const poll = async () => {
        if (cancelledRef.current) { setGenerating(false); return; }
        try {
          const status = await api.getTaskStatus(task_id);

          // Update progress from batch_progress
          if (status.batch_progress) {
            const { partial_results } = status.batch_progress;
            if (partial_results?.length) {
              setEntries(prev => {
                const next = [...prev];
                for (const pr of partial_results) {
                  const idx = next.findIndex(e => e.filename === pr.filename ||
                    e.filename === pr.filename.replace('.txt.md', '').replace('.md', ''));
                  if (idx >= 0 && next[idx].status !== 'done') {
                    next[idx] = { ...next[idx], result: pr.result, status: 'done' };
                  }
                }
                // Mark current generating
                const doneCount = next.filter(e => e.status === 'done').length;
                if (doneCount < next.length) {
                  next[doneCount] = { ...next[doneCount], status: 'generating' };
                }
                return next;
              });
            }
          }

          if (status.status === 'complete') {
            // Parse final results
            try {
              const results = typeof status.result === 'string'
                ? JSON.parse(status.result)
                : status.result;
              if (Array.isArray(results)) {
                setEntries(results.map((r: any) => ({
                  filename: r.filename,
                  result: r.result,
                  status: 'done' as const,
                })));
              }
            } catch {
              // If can't parse, just mark all done
              setEntries(prev => prev.map(e => ({ ...e, status: 'done' })));
            }
            setGenerating(false);
            setExpandedIdx(0);
          } else if (status.status === 'error') {
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
      setGenerating(false);
    }
  }, [projectName, selectedDocs, generating]);

  const handleCancel = () => {
    cancelledRef.current = true;
    setGenerating(false);
  };

  const handleReset = () => {
    setEntries([]);
    setExpandedIdx(null);
  };

  const handleExportAll = (format: 'word' | 'md' = 'word') => {
    const done = entries.filter(e => e.status === 'done' && e.result);
    if (!done.length) return;
    const md = done.map((e, i) => `# ${i + 1}. ${e.filename}\n\n${e.result}`).join('\n\n---\n\n');
    const fname = generateFilename('자료분석', format === 'word' ? 'docx' : 'md', projectName);
    if (format === 'word') downloadAsWord(md, fname);
    else downloadAsMd(md, fname);
  };

  const doneCount = entries.filter(e => e.status === 'done').length;
  const totalCount = entries.length;
  const progress = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-violet-50 flex items-center justify-center text-3xl">
              🔍
            </div>
            <div className="text-center">
              <div className="text-sm font-medium text-slate-600 mb-1">자료 분석</div>
              <div className="text-xs text-slate-400 max-w-xs leading-relaxed">
                선택한 문서들을 순차적으로 분석하여
                핵심 요약, 주요 데이터, 리스크를 정리합니다.
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 mb-2">
                {selectedDocs.length > 0
                  ? `${selectedDocs.length}개 문서 선택됨`
                  : '왼쪽에서 분석할 문서를 선택하세요'}
              </div>
              <button
                onClick={handleGenerate}
                disabled={selectedDocs.length === 0}
                className="px-6 py-2.5 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 disabled:opacity-30 transition-colors"
              >
                분석 시작
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Progress bar */}
            {generating && (
              <div className="bg-violet-50 border border-violet-200 rounded-lg px-3 py-2 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-violet-100 rounded-full overflow-hidden">
                  <div className="h-full bg-violet-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
                <span className="text-xs text-violet-600 font-medium shrink-0">{doneCount}/{totalCount}</span>
                <button onClick={handleCancel} className="text-xs text-red-500 hover:text-red-700 shrink-0">중지</button>
              </div>
            )}

            {/* Actions */}
            {doneCount > 0 && !generating && (
              <div className="flex gap-2 justify-end">
                <button onClick={() => handleExportAll('md')}
                  className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                  MD
                </button>
                <button onClick={() => handleExportAll('word')}
                  className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                  Word
                </button>
                <button onClick={handleReset}
                  className="px-3 py-1 text-xs text-slate-400 border border-slate-200 rounded-lg hover:bg-slate-50">
                  초기화
                </button>
              </div>
            )}

            {/* Entries */}
            {entries.map((entry, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                  className="w-full px-4 py-2.5 bg-slate-50 border-b border-slate-100 flex items-center gap-2 hover:bg-slate-100 transition-colors text-left"
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    entry.status === 'done' ? 'bg-green-500' :
                    entry.status === 'generating' ? 'bg-violet-500 animate-pulse' :
                    'bg-slate-300'
                  }`} />
                  <svg
                    className={`w-3 h-3 text-slate-400 transition-transform ${expandedIdx === i ? 'rotate-90' : ''}`}
                    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                  >
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                  <span className="text-sm font-medium text-slate-700 truncate flex-1">{entry.filename}</span>
                  {entry.status === 'done' && (
                    <button onClick={(e) => {
                      e.stopPropagation();
                      copyRichText(entry.result);
                      setCopiedIdx(i);
                      setTimeout(() => setCopiedIdx(null), 1500);
                    }}
                      className="text-[10px] text-slate-400 hover:text-blue-600 shrink-0">
                      {copiedIdx === i ? '✓' : '복사'}
                    </button>
                  )}
                </button>

                {expandedIdx === i && entry.result && (
                  <div className="px-4 py-3 max-h-[50vh] overflow-y-auto">
                    <MarkdownViewer content={entry.result} />
                  </div>
                )}

                {entry.status === 'generating' && expandedIdx !== i && (
                  <div className="px-4 py-2 flex items-center gap-2 text-slate-400">
                    <div className="w-3 h-3 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs">분석 중...</span>
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
