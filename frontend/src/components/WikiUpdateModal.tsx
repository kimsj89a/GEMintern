/**
 * WikiUpdateModal — 위키 갱신 3단계 워크플로
 * 1) 자료 선택 (체크박스)
 * 2) LLM 변경 제안 미리보기 (섹션별 update/keep/add)
 * 3) 사용자 컨펌 → 실제 갱신
 */
import { useEffect, useState } from 'react';
import { api } from '../api/client';

type Step = 'pick_docs' | 'review' | 'applying';

interface DocItem { name: string; }

interface Proposal {
  id: string;
  title: string;
  action: 'update' | 'keep' | 'add';
  reason: string;
  preview_summary: string;
}

interface Props {
  projectName: string;
  onClose: () => void;
  onUpdated: () => void; // 본문 반영 끝났을 때
}

export default function WikiUpdateModal({ projectName, onClose, onUpdated }: Props) {
  const [step, setStep] = useState<Step>('pick_docs');
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Step 2 state
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  // ── Step 1: docs 로드 ──
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const list = await api.listDocuments(projectName);
        setDocs(Array.isArray(list) ? list : []);
      } catch (e: any) {
        setError(e?.message || '문서 목록 로드 실패');
      } finally { setLoading(false); }
    })();
  }, [projectName]);

  const docKey = (d: any): string =>
    d?.filename || d?.name || (typeof d === 'string' ? d : '') || '';
  const allKeys = docs.map(docKey).filter(Boolean);
  const allSelected = allKeys.length > 0 && allKeys.every(k => selected.has(k));

  const toggle = (k: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k); else next.add(k);
      return next;
    });
  };

  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(allKeys));
  };

  // ── Step 1 → 2: preview 요청 ──
  const goReview = async () => {
    if (selected.size === 0) {
      setError('자료를 1개 이상 선택해주세요.');
      return;
    }
    setError(null);
    setPreviewLoading(true);
    try {
      const r = await api.previewWikiUpdate(projectName, Array.from(selected));
      setProposals(r.proposals || []);
      setStep('review');
    } catch (e: any) {
      setError(e?.message || '미리보기 실패');
    } finally { setPreviewLoading(false); }
  };

  // ── Step 2 → 3: 실제 갱신 ──
  const applyUpdate = async () => {
    setStep('applying');
    setError(null);
    try {
      const { task_id } = await api.updateWiki(projectName, Array.from(selected));
      // poll
      const poll = async (): Promise<any> => {
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') return status.result;
        if (status.status === 'error') throw new Error(status.error || '갱신 실패');
        await new Promise(r => setTimeout(r, 2000));
        return poll();
      };
      await poll();
      onUpdated();
      onClose();
    } catch (e: any) {
      setError(e?.message || '갱신 실패');
      setStep('review'); // 다시 시도 가능하게
    }
  };

  const actionBadge = (a: Proposal['action']) => {
    const map = {
      update: { label: '✏️ 갱신', cls: 'bg-amber-100 text-amber-700' },
      keep:   { label: '— 유지', cls: 'bg-slate-100 text-slate-500' },
      add:    { label: '+ 신규', cls: 'bg-emerald-100 text-emerald-700' },
    };
    const m = map[a];
    return <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${m.cls}`}>{m.label}</span>;
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-[640px] max-w-[92vw] max-h-[80vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-700">
            🔄 위키 갱신
            <span className="text-[11px] text-slate-400 ml-2">
              {step === 'pick_docs' && '1단계 · 자료 선택'}
              {step === 'review' && '2단계 · 변경 제안 검토'}
              {step === 'applying' && '3단계 · 본문 반영중'}
            </span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg">✕</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          {error && (
            <div className="m-4 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">{error}</div>
          )}

          {/* STEP 1: 자료 선택 */}
          {step === 'pick_docs' && (
            <div className="p-4">
              {loading ? (
                <div className="flex items-center justify-center py-8 text-sm text-slate-400">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-2" />
                  문서 목록 로드 중…
                </div>
              ) : docs.length === 0 ? (
                <div className="text-sm text-slate-400 py-6 text-center">프로젝트에 업로드된 문서가 없습니다.</div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs text-slate-500">어떤 자료로 위키를 갱신할까요?</div>
                    <button onClick={toggleAll}
                      className="text-[11px] text-blue-600 hover:text-blue-800">
                      {allSelected ? '전체 해제' : '전체 선택'}
                    </button>
                  </div>
                  <div className="border border-slate-200 rounded-lg max-h-80 overflow-y-auto">
                    {docs.map((d, i) => {
                      const k = docKey(d);
                      if (!k) return null;
                      const checked = selected.has(k);
                      return (
                        <label key={`${k}-${i}`}
                          className={`flex items-center gap-2 px-3 py-2 border-b border-slate-100 last:border-b-0 cursor-pointer text-xs ${
                            checked ? 'bg-blue-50' : 'hover:bg-slate-50'
                          }`}>
                          <input type="checkbox" checked={checked} onChange={() => toggle(k)}
                            className="w-4 h-4 accent-blue-600" />
                          <span className="flex-1 truncate text-slate-700">{k.replace(/\.(md|pdf|docx?|pptx?|xlsx?|txt)$/i, '')}</span>
                          <span className="text-[10px] text-slate-400">{(k.match(/\.[a-z0-9]+$/i)?.[0] || '').toLowerCase()}</span>
                        </label>
                      );
                    })}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-2">
                    선택됨: {selected.size}개 / 총 {docs.length}개
                  </div>
                </>
              )}
            </div>
          )}

          {/* STEP 2: 변경 제안 */}
          {step === 'review' && (
            <div className="p-4 space-y-2">
              <div className="text-xs text-slate-500 mb-2">
                자료 {selected.size}개 분석 결과 · 아래 변경사항을 적용하시겠습니까?
              </div>
              {proposals.length === 0 ? (
                <div className="text-sm text-slate-400 py-6 text-center">변경 제안이 없습니다.</div>
              ) : (
                <div className="border border-slate-200 rounded-lg divide-y divide-slate-100">
                  {proposals.map((p, i) => (
                    <div key={`${p.id}-${i}`} className="p-3">
                      <div className="flex items-start gap-2">
                        {actionBadge(p.action)}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-slate-800 truncate">{p.title}</div>
                          {p.preview_summary && (
                            <div className="text-[12px] text-slate-700 mt-0.5">{p.preview_summary}</div>
                          )}
                          {p.reason && (
                            <div className="text-[11px] text-slate-500 italic mt-0.5">↳ {p.reason}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* STEP 3: 적용중 */}
          {step === 'applying' && (
            <div className="p-8 flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <div className="text-sm text-slate-600">본문에 반영하는 중…</div>
              <div className="text-[11px] text-slate-400">자료 분석 → 섹션별 작성 → 출처 정리</div>
            </div>
          )}
        </div>

        {/* Footer */}
        {step !== 'applying' && (
          <div className="px-5 py-3 border-t border-slate-200 flex justify-between items-center bg-slate-50">
            <div>
              {step === 'review' && (
                <button onClick={() => setStep('pick_docs')}
                  className="text-xs text-slate-500 hover:text-slate-700">← 자료 다시 선택</button>
              )}
            </div>
            <div className="flex gap-2">
              <button onClick={onClose}
                className="px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100 rounded-lg">취소</button>
              {step === 'pick_docs' && (
                <button onClick={goReview}
                  disabled={previewLoading || selected.size === 0}
                  className="px-4 py-1.5 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-40">
                  {previewLoading ? (
                    <span className="flex items-center gap-2">
                      <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      분석중…
                    </span>
                  ) : `다음: 변경 제안 받기 →`}
                </button>
              )}
              {step === 'review' && (
                <button onClick={applyUpdate}
                  className="px-4 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">
                  ✅ 본문에 반영
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
