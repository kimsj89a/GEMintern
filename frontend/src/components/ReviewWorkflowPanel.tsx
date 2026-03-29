import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useAppStore } from '../stores/appStore';

interface RfiItem {
  id: string;
  category: string;
  question: string;
  priority: '상' | '중' | '하';
  wiki_section?: string;
  status?: string;
}

interface CrosscheckItem extends RfiItem {
  coverage: 'covered' | 'partial' | 'gap';
  source_doc?: string;
  source_excerpt?: string;
  explanation?: string;
}

interface CrosscheckSummary {
  total: number;
  covered: number;
  partial: number;
  gap: number;
}

interface WikiInfo {
  sections: { id: string; title: string }[];
  generated_at: string | null;
}

const STEPS = [
  { id: 1, label: '위키 생성', icon: '📖' },
  { id: 2, label: 'RFI 추출', icon: '📋' },
  { id: 3, label: '교차검증', icon: '🔍' },
];

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  financial: { label: '재무', color: 'bg-green-100 text-green-700' },
  legal: { label: '법률', color: 'bg-red-100 text-red-700' },
  market: { label: '시장', color: 'bg-blue-100 text-blue-700' },
  business: { label: '사업', color: 'bg-purple-100 text-purple-700' },
  valuation: { label: '밸류', color: 'bg-amber-100 text-amber-700' },
  general: { label: '기타', color: 'bg-slate-100 text-slate-700' },
};

const PRIORITY_COLORS: Record<string, string> = {
  '상': 'text-red-600 bg-red-50',
  '중': 'text-amber-600 bg-amber-50',
  '하': 'text-slate-500 bg-slate-50',
};

export default function ReviewWorkflowPanel({ projectName }: { projectName: string }) {
  const [step, setStep] = useState(1);
  const [cycle, setCycle] = useState(1);

  // Step 1 state
  const [wiki, setWiki] = useState<WikiInfo | null>(null);
  const [wikiLoading, setWikiLoading] = useState(false);
  const [wikiGenerating, setWikiGenerating] = useState(false);

  // Step 2 state
  const [rfiItems, setRfiItems] = useState<RfiItem[]>([]);
  const [rfiLoading, setRfiLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [addingItem, setAddingItem] = useState(false);
  const [newQuestion, setNewQuestion] = useState('');
  const [newCategory, setNewCategory] = useState('general');
  const [newPriority, setNewPriority] = useState<'상' | '중' | '하'>('중');

  // Step 3 state
  const [crosscheckItems, setCrosscheckItems] = useState<CrosscheckItem[]>([]);
  const [crosscheckSummary, setCrosscheckSummary] = useState<CrosscheckSummary | null>(null);
  const [crosscheckLoading, setCrosscheckLoading] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load wiki info on mount
  useEffect(() => {
    loadWiki();
  }, [projectName]);

  const loadWiki = useCallback(async () => {
    setWikiLoading(true);
    try {
      const data = await api.getWiki(projectName);
      if (data && data.sections?.length > 0) {
        setWiki({
          sections: data.sections.map((s: any) => ({ id: s.id, title: s.title })),
          generated_at: data.generated_at,
        });
      } else {
        setWiki(null);
      }
    } catch {
      setWiki(null);
    }
    setWikiLoading(false);
  }, [projectName]);

  // Poll helper
  const pollTask = useCallback((taskId: string, onComplete: (result: any) => void, onError: (err: string) => void) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getTaskStatus(taskId);
        if (status.status === 'complete') {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          onComplete(status.result);
        } else if (status.status === 'error') {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          onError(status.error || '알 수 없는 오류');
        }
      } catch {
        clearInterval(pollRef.current!);
        pollRef.current = null;
        onError('폴링 오류');
      }
    }, 2000);
  }, []);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // Step 1: Generate / Update wiki
  const handleWikiGenerate = async (update = false) => {
    setWikiGenerating(true);
    try {
      const res = update ? await api.updateWiki(projectName) : await api.generateWiki(projectName);
      pollTask(res.task_id,
        () => { loadWiki(); setWikiGenerating(false); },
        (err) => { alert(`위키 생성 오류: ${err}`); setWikiGenerating(false); },
      );
    } catch (e: any) {
      alert(`오류: ${e.message}`);
      setWikiGenerating(false);
    }
  };

  // Step 2: Extract RFI
  const handleExtractRfi = async () => {
    setRfiLoading(true);
    try {
      const res = await api.extractRfi(projectName);
      pollTask(res.task_id,
        (result) => {
          setRfiItems(result?.items || []);
          setRfiLoading(false);
        },
        (err) => { alert(`RFI 추출 오류: ${err}`); setRfiLoading(false); },
      );
    } catch (e: any) {
      alert(`오류: ${e.message}`);
      setRfiLoading(false);
    }
  };

  const handleDeleteRfi = (id: string) => {
    setRfiItems(prev => prev.filter(it => it.id !== id));
  };

  const handleEditSave = (id: string) => {
    setRfiItems(prev => prev.map(it => it.id === id ? { ...it, question: editText } : it));
    setEditingId(null);
  };

  const handleAddItem = () => {
    if (!newQuestion.trim()) return;
    const id = `rfi_manual_${Date.now()}`;
    setRfiItems(prev => [...prev, { id, category: newCategory, question: newQuestion.trim(), priority: newPriority }]);
    setNewQuestion('');
    setAddingItem(false);
  };

  // Step 3: Crosscheck
  const handleCrosscheck = async () => {
    setCrosscheckLoading(true);
    try {
      const res = await api.crosscheckRfi(projectName, rfiItems);
      pollTask(res.task_id,
        (result) => {
          setCrosscheckItems(result?.items || []);
          setCrosscheckSummary(result?.summary || null);
          setCrosscheckLoading(false);
        },
        (err) => { alert(`교차검증 오류: ${err}`); setCrosscheckLoading(false); },
      );
    } catch (e: any) {
      alert(`오류: ${e.message}`);
      setCrosscheckLoading(false);
    }
  };

  const goToReport = (_template: string) => {
    const store = useAppStore.getState();
    store.setView('legacy');
    store.openTab('phase2');
  };

  // Render
  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold text-slate-800">검토 워크플로</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">{cycle}차 검토</span>
        </div>
      </div>

      {/* Step indicator */}
      <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-1 shrink-0">
        {STEPS.map((s, i) => {
          const isActive = step === s.id;
          const isDone = step > s.id;
          return (
            <div key={s.id} className="flex items-center">
              <button
                onClick={() => setStep(s.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-semibold'
                    : isDone
                      ? 'text-blue-500 hover:bg-blue-50/50'
                      : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  isActive ? 'bg-blue-600 text-white' : isDone ? 'bg-blue-200 text-blue-700' : 'bg-slate-200 text-slate-500'
                }`}>{isDone ? '✓' : s.id}</span>
                <span>{s.label}</span>
              </button>
              {i < STEPS.length - 1 && (
                <div className={`w-6 h-px mx-1 ${isDone ? 'bg-blue-300' : 'bg-slate-200'}`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {step === 1 && (
          <Step1Wiki
            wiki={wiki}
            loading={wikiLoading}
            generating={wikiGenerating}
            onGenerate={handleWikiGenerate}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <Step2Rfi
            items={rfiItems}
            loading={rfiLoading}
            editingId={editingId}
            editText={editText}
            addingItem={addingItem}
            newQuestion={newQuestion}
            newCategory={newCategory}
            newPriority={newPriority}
            onExtract={handleExtractRfi}
            onDelete={handleDeleteRfi}
            onEditStart={(id, text) => { setEditingId(id); setEditText(text); }}
            onEditChange={setEditText}
            onEditSave={handleEditSave}
            onEditCancel={() => setEditingId(null)}
            onAddToggle={() => setAddingItem(!addingItem)}
            onNewQuestionChange={setNewQuestion}
            onNewCategoryChange={setNewCategory}
            onNewPriorityChange={setNewPriority}
            onAddItem={handleAddItem}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <Step3Crosscheck
            items={crosscheckItems}
            summary={crosscheckSummary}
            loading={crosscheckLoading}
            rfiCount={rfiItems.length}
            onCrosscheck={handleCrosscheck}
            onGoToReport={goToReport}
            onNewCycle={() => { setCycle(c => c + 1); setStep(1); setRfiItems([]); setCrosscheckItems([]); setCrosscheckSummary(null); }}
          />
        )}
      </div>
    </div>
  );
}


/* ────── Step 1: Wiki ────── */

function Step1Wiki({ wiki, loading, generating, onGenerate, onNext }: {
  wiki: WikiInfo | null;
  loading: boolean;
  generating: boolean;
  onGenerate: (update?: boolean) => void;
  onNext: () => void;
}) {
  return (
    <div className="p-5 space-y-4">
      <div className="text-sm text-slate-600">
        프로젝트 자료를 기반으로 위키를 생성합니다. 위키가 있어야 다음 단계를 진행할 수 있습니다.
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-8 justify-center text-slate-400">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">위키 로딩 중...</span>
        </div>
      ) : wiki ? (
        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm font-medium text-slate-700">위키 생성됨</span>
              <span className="text-xs text-slate-400">{wiki.sections.length}개 섹션</span>
            </div>
            {wiki.generated_at && (
              <span className="text-xs text-slate-400">{new Date(wiki.generated_at).toLocaleDateString('ko')}</span>
            )}
          </div>
          <div className="space-y-1">
            {wiki.sections.map(s => (
              <div key={s.id} className="text-xs text-slate-500 pl-3 border-l-2 border-slate-200 py-0.5">
                {s.title}
              </div>
            ))}
          </div>
          <div className="flex gap-2 pt-2">
            <button
              onClick={() => onGenerate(true)}
              disabled={generating}
              className="px-3 py-1.5 text-xs bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 disabled:opacity-50 transition-colors"
            >
              {generating ? '갱신 중...' : '위키 갱신'}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl p-8 flex flex-col items-center gap-3">
          <span className="text-3xl opacity-50">📖</span>
          <span className="text-sm text-slate-500">위키가 아직 생성되지 않았습니다</span>
          <button
            onClick={() => onGenerate(false)}
            disabled={generating}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                생성 중...
              </span>
            ) : '위키 생성'}
          </button>
        </div>
      )}

      <div className="flex justify-end pt-2">
        <button
          onClick={onNext}
          disabled={!wiki}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
        >
          다음 단계 <span className="text-xs">→</span>
        </button>
      </div>
    </div>
  );
}


/* ────── Step 2: RFI Extraction ────── */

function Step2Rfi({ items, loading, editingId, editText, addingItem, newQuestion, newCategory, newPriority,
  onExtract, onDelete, onEditStart, onEditChange, onEditSave, onEditCancel, onAddToggle,
  onNewQuestionChange, onNewCategoryChange, onNewPriorityChange, onAddItem, onNext }: {
  items: RfiItem[];
  loading: boolean;
  editingId: string | null;
  editText: string;
  addingItem: boolean;
  newQuestion: string;
  newCategory: string;
  newPriority: '상' | '중' | '하';
  onExtract: () => void;
  onDelete: (id: string) => void;
  onEditStart: (id: string, text: string) => void;
  onEditChange: (text: string) => void;
  onEditSave: (id: string) => void;
  onEditCancel: () => void;
  onAddToggle: () => void;
  onNewQuestionChange: (v: string) => void;
  onNewCategoryChange: (v: string) => void;
  onNewPriorityChange: (v: '상' | '중' | '하') => void;
  onAddItem: () => void;
  onNext: () => void;
}) {
  return (
    <div className="p-5 space-y-4">
      <div className="text-sm text-slate-600">
        위키 내용을 분석하여 추가 확인이 필요한 Q&A/RFI 항목을 추출합니다.
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onExtract}
          disabled={loading}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              분석 중...
            </span>
          ) : items.length > 0 ? '다시 추출' : '위키에서 RFI 추출'}
        </button>
        <button
          onClick={onAddToggle}
          className="px-3 py-2 text-sm text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
        >
          + 항목 추가
        </button>
        {items.length > 0 && (
          <span className="text-xs text-slate-400 ml-auto">{items.length}건</span>
        )}
      </div>

      {/* Add item form */}
      {addingItem && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 space-y-2">
          <textarea
            value={newQuestion}
            onChange={e => onNewQuestionChange(e.target.value)}
            placeholder="확인이 필요한 사항을 입력하세요..."
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-blue-400 resize-none"
            rows={2}
          />
          <div className="flex items-center gap-2">
            <select value={newCategory} onChange={e => onNewCategoryChange(e.target.value)}
              className="text-xs px-2 py-1 border border-slate-200 rounded-lg">
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
            <select value={newPriority} onChange={e => onNewPriorityChange(e.target.value as any)}
              className="text-xs px-2 py-1 border border-slate-200 rounded-lg">
              <option value="상">우선순위: 상</option>
              <option value="중">우선순위: 중</option>
              <option value="하">우선순위: 하</option>
            </select>
            <div className="ml-auto flex gap-1">
              <button onClick={onAddItem} className="px-3 py-1 text-xs bg-blue-600 text-white rounded-lg">추가</button>
              <button onClick={onAddToggle} className="px-3 py-1 text-xs text-slate-500 border rounded-lg">취소</button>
            </div>
          </div>
        </div>
      )}

      {/* RFI items list */}
      {items.length > 0 && (
        <div className="space-y-2">
          {items.map(item => {
            const cat = CATEGORY_LABELS[item.category] || CATEGORY_LABELS.general;
            const priColor = PRIORITY_COLORS[item.priority] || PRIORITY_COLORS['중'];
            return (
              <div key={item.id} className="bg-white border border-slate-200 rounded-xl p-3 group hover:border-slate-300 transition-colors">
                <div className="flex items-start gap-2">
                  <div className="flex flex-col gap-1 shrink-0 pt-0.5">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${cat.color}`}>{cat.label}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium text-center ${priColor}`}>{item.priority}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    {editingId === item.id ? (
                      <div className="space-y-1">
                        <textarea value={editText} onChange={e => onEditChange(e.target.value)}
                          className="w-full px-2 py-1 text-sm border border-blue-300 rounded-lg focus:outline-none resize-none" rows={2} />
                        <div className="flex gap-1">
                          <button onClick={() => onEditSave(item.id)} className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded">저장</button>
                          <button onClick={onEditCancel} className="px-2 py-0.5 text-xs text-slate-500 border rounded">취소</button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-slate-700 leading-relaxed">{item.question}</div>
                    )}
                    {item.wiki_section && (
                      <div className="text-[10px] text-slate-400 mt-1">
                        관련 섹션: {item.wiki_section}
                      </div>
                    )}
                  </div>
                  {editingId !== item.id && (
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button onClick={() => onEditStart(item.id, item.question)} className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-blue-600 rounded hover:bg-blue-50" title="편집">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button onClick={() => onDelete(item.id)} className="w-6 h-6 flex items-center justify-center text-slate-400 hover:text-red-600 rounded hover:bg-red-50" title="삭제">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {items.length === 0 && !loading && (
        <div className="py-8 text-center text-sm text-slate-400">
          아직 추출된 항목이 없습니다. 위 버튼을 눌러 위키에서 RFI를 추출하세요.
        </div>
      )}

      <div className="flex justify-between pt-2">
        <button onClick={() => {}} className="text-sm text-slate-400" disabled>
          {/* placeholder */}
        </button>
        <button
          onClick={onNext}
          disabled={items.length === 0}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
        >
          교차검증으로 <span className="text-xs">→</span>
        </button>
      </div>
    </div>
  );
}


/* ────── Step 3: Cross-check ────── */

function Step3Crosscheck({ items, summary, loading, rfiCount, onCrosscheck, onGoToReport, onNewCycle }: {
  items: CrosscheckItem[];
  summary: CrosscheckSummary | null;
  loading: boolean;
  rfiCount: number;
  onCrosscheck: () => void;
  onGoToReport: (template: string) => void;
  onNewCycle: () => void;
}) {
  const coverageIcon = (c: string) => {
    if (c === 'covered') return { icon: '✅', label: '커버됨', cls: 'text-green-600 bg-green-50' };
    if (c === 'partial') return { icon: '⚠️', label: '부분', cls: 'text-amber-600 bg-amber-50' };
    return { icon: '❌', label: '미커버', cls: 'text-red-600 bg-red-50' };
  };

  return (
    <div className="p-5 space-y-4">
      <div className="text-sm text-slate-600">
        RFI 항목({rfiCount}건)을 원본 소스 문서와 교차검증합니다.
      </div>

      <button
        onClick={onCrosscheck}
        disabled={loading}
        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            검증 중...
          </span>
        ) : items.length > 0 ? '다시 검증' : '원본 자료와 교차검증'}
      </button>

      {/* Summary bar */}
      {summary && (
        <div className="bg-white border border-slate-200 rounded-xl p-3 flex items-center gap-4">
          <span className="text-sm font-medium text-slate-700">검증 결과</span>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              커버 {summary.covered}건
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              부분 {summary.partial}건
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              미커버 {summary.gap}건
            </span>
          </div>
          <span className="text-xs text-slate-400 ml-auto">총 {summary.total}건</span>
        </div>
      )}

      {/* Results table */}
      {items.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 w-16">상태</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500">항목</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 w-28">출처</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 hidden md:table-cell">설명</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => {
                const cov = coverageIcon(item.coverage);
                return (
                  <tr key={item.id} className="border-b border-slate-100 hover:bg-slate-50/50">
                    <td className="px-3 py-2.5">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${cov.cls}`}>
                        {cov.icon} {cov.label}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="text-sm text-slate-700 leading-snug">{item.question}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      {item.source_doc ? (
                        <span className="text-xs text-blue-600 truncate block max-w-[120px]" title={item.source_doc}>
                          {item.source_doc}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-300">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 hidden md:table-cell">
                      <div className="text-xs text-slate-500 line-clamp-2">{item.explanation || item.source_excerpt || '—'}</div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {items.length === 0 && !loading && (
        <div className="py-8 text-center text-sm text-slate-400">
          아직 검증 결과가 없습니다. 위 버튼을 눌러 교차검증을 실행하세요.
        </div>
      )}

      {/* Report shortcuts + loop */}
      {items.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">보고서 생성</div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => onGoToReport('simple_review')}
              className="px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-sm transition-all flex items-center gap-2 group">
              <span className="text-lg">📋</span>
              <div className="text-left">
                <div className="font-medium text-slate-700 group-hover:text-blue-700">예비검토보고서</div>
                <div className="text-[10px] text-slate-400">Quick Memo</div>
              </div>
            </button>
            <button onClick={() => onGoToReport('investment')}
              className="px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-xl hover:border-blue-300 hover:shadow-sm transition-all flex items-center gap-2 group">
              <span className="text-lg">💰</span>
              <div className="text-left">
                <div className="font-medium text-slate-700 group-hover:text-blue-700">투자심사보고서</div>
                <div className="text-[10px] text-slate-400">IC 심의용</div>
              </div>
            </button>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={onNewCycle}
              className="px-4 py-2 text-sm text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors flex items-center gap-1"
            >
              <span>🔄</span> 새 사이클 시작 (외부자료 수령 후)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
