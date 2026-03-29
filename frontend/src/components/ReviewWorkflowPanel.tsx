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
  { id: 4, label: '문서 생성', icon: '📄' },
  { id: 5, label: '외부 요청', icon: '📨' },
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

  // Step 4 state
  const [generatedDoc, setGeneratedDoc] = useState('');
  const [docGenerating, setDocGenerating] = useState(false);
  const [wikiSections, setWikiSections] = useState<{ id: string; title: string; order: number }[]>([]);
  const [insertTarget, setInsertTarget] = useState<string | null>(null);

  // Step 5 state
  const [externalRfi, setExternalRfi] = useState('');
  const [externalRfiLoading, setExternalRfiLoading] = useState(false);

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

  // Step 4: Generate report
  const handleGenerateReport = async (template: string) => {
    setDocGenerating(true);
    try {
      const res = await api.startGenerate({
        project_name: projectName,
        template_option: template,
        mode: 'chained',
        inputs: { template_option: template },
      });
      pollTask(res.task_id,
        (result) => {
          setGeneratedDoc(typeof result === 'string' ? result : result?.text || result?.result || JSON.stringify(result));
          setDocGenerating(false);
        },
        (err) => { alert(`보고서 생성 오류: ${err}`); setDocGenerating(false); },
      );
    } catch (e: any) {
      alert(`오류: ${e.message}`);
      setDocGenerating(false);
    }
  };

  // Load full wiki sections for step 4
  const loadWikiSections = useCallback(async () => {
    try {
      const data = await api.getWiki(projectName);
      if (data?.sections) {
        setWikiSections(data.sections.map((s: any) => ({ id: s.id, title: s.title, order: s.order ?? 0 })));
      }
    } catch {}
  }, [projectName]);

  // Insert doc section into wiki
  const handleInsertToWiki = async (content: string, _afterSectionId: string | null) => {
    const sectionId = `inserted_${Date.now()}`;
    const title = content.split('\n')[0]?.replace(/^#+\s*/, '').slice(0, 50) || '삽입된 섹션';
    try {
      await api.addWikiSection(projectName, { id: sectionId, title, content });
      await loadWikiSections();
      setInsertTarget(null);
    } catch (e: any) {
      alert(`위키 삽입 오류: ${e.message}`);
    }
  };

  // Step 5: Generate external RFI document
  const handleGenerateExternalRfi = async () => {
    const gapItems = crosscheckItems.filter(it => it.coverage === 'gap' || it.coverage === 'partial');
    if (gapItems.length === 0) { alert('미커버/부분 항목이 없습니다.'); return; }
    setExternalRfiLoading(true);
    try {
      const res = await api.generateExternalRfi(projectName, gapItems);
      pollTask(res.task_id,
        (result) => {
          setExternalRfi(result?.rfi_document || '');
          setExternalRfiLoading(false);
        },
        (err) => { alert(`RFI 문서 생성 오류: ${err}`); setExternalRfiLoading(false); },
      );
    } catch (e: any) {
      alert(`오류: ${e.message}`);
      setExternalRfiLoading(false);
    }
  };

  const handleNewCycle = () => {
    setCycle(c => c + 1);
    setStep(1);
    setRfiItems([]);
    setCrosscheckItems([]);
    setCrosscheckSummary(null);
    setGeneratedDoc('');
    setExternalRfi('');
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
            onNextDoc={() => { loadWikiSections(); setStep(4); }}
            onNextExternal={() => setStep(5)}
          />
        )}
        {step === 4 && (
          <Step4SplitDoc
            generatedDoc={generatedDoc}
            generating={docGenerating}
            wikiSections={wikiSections}
            insertTarget={insertTarget}
            onGenerate={handleGenerateReport}
            onInsert={handleInsertToWiki}
            onSetInsertTarget={setInsertTarget}
            onGoToReport={goToReport}
          />
        )}
        {step === 5 && (
          <Step5ExternalRequest
            crosscheckItems={crosscheckItems}
            externalRfi={externalRfi}
            loading={externalRfiLoading}
            onGenerate={handleGenerateExternalRfi}
            onNewCycle={handleNewCycle}
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

function Step3Crosscheck({ items, summary, loading, rfiCount, onCrosscheck, onNextDoc, onNextExternal }: {
  items: CrosscheckItem[];
  summary: CrosscheckSummary | null;
  loading: boolean;
  rfiCount: number;
  onCrosscheck: () => void;
  onNextDoc: () => void;
  onNextExternal: () => void;
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

      {/* Next steps */}
      {items.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-3">
          <button onClick={onNextDoc}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-1">
            문서 생성 + 위키 삽입 <span className="text-xs">→</span>
          </button>
          <button onClick={onNextExternal}
            className="px-4 py-2 text-sm text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors flex items-center gap-1">
            외부 자료 요청 <span className="text-xs">→</span>
          </button>
        </div>
      )}
    </div>
  );
}


/* ────── Step 4: Split Doc + Wiki Insertion ────── */

function Step4SplitDoc({ generatedDoc, generating, wikiSections, insertTarget,
  onGenerate, onInsert, onSetInsertTarget, onGoToReport }: {
  generatedDoc: string;
  generating: boolean;
  wikiSections: { id: string; title: string; order: number }[];
  insertTarget: string | null;
  onGenerate: (template: string) => void;
  onInsert: (content: string, afterSectionId: string | null) => void;
  onSetInsertTarget: (id: string | null) => void;
  onGoToReport: (template: string) => void;
}) {
  const [selectedText, setSelectedText] = useState('');
  const [draggedSection, setDraggedSection] = useState<string | null>(null);

  // Split generated doc into sections by headings
  const docSections = generatedDoc
    ? generatedDoc.split(/(?=^#{1,3}\s)/m).filter(s => s.trim())
    : [];

  return (
    <div className="flex flex-col h-full">
      {/* Template buttons */}
      <div className="px-5 py-3 border-b border-slate-100 space-y-2 shrink-0">
        <div className="text-sm text-slate-600">보고서를 생성한 후 원하는 섹션을 위키에 삽입합니다.</div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => onGenerate('simple_review')} disabled={generating}
            className="px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:border-blue-300 transition-all flex items-center gap-1.5 disabled:opacity-50">
            <span>📋</span> 예비검토보고서
          </button>
          <button onClick={() => onGenerate('investment')} disabled={generating}
            className="px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:border-blue-300 transition-all flex items-center gap-1.5 disabled:opacity-50">
            <span>💰</span> 투자심사보고서
          </button>
          <button onClick={() => onGoToReport('phase2')}
            className="px-3 py-2 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50 transition-all">
            기타 보고서...
          </button>
        </div>
      </div>

      {generating && (
        <div className="flex items-center justify-center gap-2 py-12 text-slate-400">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">보고서 생성 중...</span>
        </div>
      )}

      {/* Split view */}
      {!generating && generatedDoc && (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Generated document sections */}
          <div className="flex-1 overflow-y-auto border-r border-slate-200">
            <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 sticky top-0 z-10">
              <span className="text-xs font-semibold text-slate-500">생성된 문서</span>
              <span className="text-xs text-slate-400 ml-2">{docSections.length}개 섹션</span>
            </div>
            <div className="divide-y divide-slate-100">
              {docSections.map((sec, i) => {
                const title = sec.split('\n')[0]?.replace(/^#+\s*/, '').trim() || `섹션 ${i + 1}`;
                const isSelected = selectedText === sec;
                return (
                  <div
                    key={i}
                    draggable
                    onDragStart={() => setDraggedSection(sec)}
                    onDragEnd={() => setDraggedSection(null)}
                    className={`px-4 py-3 cursor-grab active:cursor-grabbing hover:bg-blue-50/30 transition-colors ${isSelected ? 'bg-blue-50 ring-1 ring-blue-200' : ''}`}
                    onClick={() => setSelectedText(isSelected ? '' : sec)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-700 truncate">{title}</div>
                        <div className="text-xs text-slate-400 mt-0.5 line-clamp-2">
                          {sec.split('\n').slice(1).join(' ').trim().slice(0, 120)}
                        </div>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedText(sec); onSetInsertTarget('__pick__'); }}
                        className="shrink-0 px-2 py-1 text-[10px] text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                        title="위키에 삽입"
                      >
                        삽입 →
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Wiki sections with drop zones */}
          <div className="w-[260px] shrink-0 overflow-y-auto">
            <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 sticky top-0 z-10">
              <span className="text-xs font-semibold text-slate-500">위키 섹션</span>
              <span className="text-xs text-slate-400 ml-2">{wikiSections.length}개</span>
            </div>
            {/* Top drop zone */}
            <DropZone
              active={!!draggedSection || insertTarget === '__pick__'}
              onDrop={() => { if (draggedSection) onInsert(draggedSection, null); }}
              onClick={() => { if (selectedText) { onInsert(selectedText, null); setSelectedText(''); } }}
              showClick={insertTarget === '__pick__'}
            />
            {wikiSections.sort((a, b) => a.order - b.order).map(s => (
              <div key={s.id}>
                <div className="px-3 py-2 text-sm text-slate-700 border-b border-slate-100 bg-white">
                  <span className="text-slate-400 mr-1">📄</span> {s.title}
                </div>
                <DropZone
                  active={!!draggedSection || insertTarget === '__pick__'}
                  onDrop={() => { if (draggedSection) onInsert(draggedSection, s.id); }}
                  onClick={() => { if (selectedText) { onInsert(selectedText, s.id); setSelectedText(''); } }}
                  showClick={insertTarget === '__pick__'}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {!generating && !generatedDoc && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-slate-400">
            <span className="text-3xl block mb-2 opacity-40">📄</span>
            <span className="text-sm">위에서 보고서 템플릿을 선택하여 문서를 생성하세요</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* Drop zone component for wiki insertion */
function DropZone({ active, onDrop, onClick, showClick }: {
  active: boolean; onDrop: () => void; onClick: () => void; showClick: boolean;
}) {
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(e) => { if (active) { e.preventDefault(); setOver(true); } }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); onDrop(); }}
      onClick={() => { if (showClick) onClick(); }}
      className={`transition-all ${
        over
          ? 'h-10 bg-blue-100 border-2 border-dashed border-blue-400 flex items-center justify-center'
          : active
            ? 'h-7 bg-blue-50/50 border border-dashed border-blue-200 flex items-center justify-center cursor-pointer hover:bg-blue-100/50'
            : 'h-0.5 bg-transparent'
      }`}
    >
      {(over || (active && showClick)) && (
        <span className="text-[10px] text-blue-500 font-medium truncate px-2">{over ? '여기에 놓기' : '클릭하여 삽입'}</span>
      )}
    </div>
  );
}


/* ────── Step 5: External Request ────── */

function Step5ExternalRequest({ crosscheckItems, externalRfi, loading, onGenerate, onNewCycle }: {
  crosscheckItems: CrosscheckItem[];
  externalRfi: string;
  loading: boolean;
  onGenerate: () => void;
  onNewCycle: () => void;
}) {
  const gapCount = crosscheckItems.filter(it => it.coverage === 'gap' || it.coverage === 'partial').length;

  const handleCopy = () => {
    navigator.clipboard.writeText(externalRfi);
  };

  const handleDownload = () => {
    const blob = new Blob([externalRfi], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `RFI_자료요청서_${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-5 space-y-4">
      <div className="text-sm text-slate-600">
        교차검증에서 미커버/부분 항목({gapCount}건)을 기반으로 외부 자료요청서를 생성합니다.
      </div>

      <button
        onClick={onGenerate}
        disabled={loading || gapCount === 0}
        className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            생성 중...
          </span>
        ) : externalRfi ? '다시 생성' : '자료요청서 생성'}
      </button>

      {gapCount === 0 && (
        <div className="text-xs text-green-600 bg-green-50 px-3 py-2 rounded-lg">
          모든 항목이 소스 문서에서 커버됩니다. 외부 자료 요청이 필요하지 않습니다.
        </div>
      )}

      {externalRfi && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">생성된 자료요청서</span>
            <div className="ml-auto flex gap-1">
              <button onClick={handleCopy} className="px-2 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                복사
              </button>
              <button onClick={handleDownload} className="px-2 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                다운로드
              </button>
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 max-h-[400px] overflow-y-auto">
            <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">{externalRfi}</pre>
          </div>
        </div>
      )}

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
        <div className="text-sm font-medium text-amber-800">외부 자료 수령 후</div>
        <div className="text-xs text-amber-600">
          요청한 자료를 수령하면, 프로젝트 소스에 업로드한 후 "새 사이클 시작"을 눌러 위키를 갱신하고 다시 검토를 진행하세요.
        </div>
        <button
          onClick={onNewCycle}
          className="px-4 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors flex items-center gap-1"
        >
          <span>🔄</span> 새 사이클 시작
        </button>
      </div>
    </div>
  );
}
