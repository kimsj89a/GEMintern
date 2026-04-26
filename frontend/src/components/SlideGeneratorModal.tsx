/**
 * SlideGeneratorModal — NotebookLM 스타일 슬라이드 맞춤설정 모달
 * 형식/템플릿/길이 선택 → 인터랙티브 플래닝(채팅) → 생성 → 미리보기 → 다운로드
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import { generateFilename } from '../utils/clipboard';
import SlidePreview from './SlidePreview';

interface Props {
  onClose: () => void;
  selectedDocs?: string[];
}

type Format = 'detailed' | 'presentation';
type Length = 'short' | 'default' | 'detailed';
type DeckMode = 'teaser' | 'im';

interface PlanSlide { title: string; type_hint?: string; purpose?: string }
interface PlanSection { title: string; key_message?: string; slide_count?: number; slides: PlanSlide[] }
interface DeckPlan { title?: string; audience?: string; tone?: string; estimated_total_slides?: number; sections: PlanSection[] }
interface ChatTurn { role: 'assistant' | 'user'; text: string }

// PR7: 슬라이드별 피드백 이력 (보존)
interface SlideRevision { feedback: string; prevSlide: any; newSlide: any; at: string; }

// PR3: outline 단계 template type 옵션 (planner type_hint + mckinsey 매핑 키 동일)
const TYPE_HINT_OPTIONS: { value: string; label: string; group: string }[] = [
  { value: 'title', label: '표지', group: '구조' },
  { value: 'divider', label: '섹션 구분', group: '구조' },
  { value: 'agenda', label: '목차', group: '구조' },
  { value: 'executive_summary', label: 'Executive Summary', group: '요약' },
  { value: 'pull_quote', label: '인용', group: '요약' },
  { value: 'stat_hero', label: 'Big Number', group: '요약' },
  { value: 'kpi_dashboard', label: 'KPI Dashboard', group: '숫자' },
  { value: 'data_table', label: '데이터 테이블', group: '숫자' },
  { value: 'two_column', label: '2단 비교', group: '비교' },
  { value: 'comparison', label: '비교 테이블', group: '비교' },
  { value: 'before_after', label: 'Before/After', group: '비교' },
  { value: 'pros_cons', label: 'Pros/Cons', group: '비교' },
  { value: 'risk_matrix', label: 'Risk Matrix', group: '매트릭스' },
  { value: 'bcg_matrix', label: 'BCG/Growth-Share', group: '매트릭스' },
  { value: 'column_chart', label: 'Column Chart', group: '차트' },
  { value: 'line_chart', label: 'Line Chart', group: '차트' },
  { value: 'bubble_chart', label: 'Bubble Chart', group: '차트' },
  { value: 'stacked_column', label: 'Stacked Column', group: '차트' },
  { value: 'timeline_flow', label: 'Phases (Chevron)', group: '프로세스' },
  { value: 'process_flow', label: 'Process Flow', group: '프로세스' },
  { value: 'funnel', label: 'Funnel', group: '프로세스' },
  { value: 'gantt', label: 'Gantt Timeline', group: '프로세스' },
  { value: 'org_chart', label: '조직도', group: '조직' },
  { value: 'numbered_blocks', label: '번호 블록', group: '일반' },
  { value: 'grid_cards', label: '그리드 카드', group: '일반' },
];

const LENGTH_OPTIONS: { id: Length; label: string; pages: string }[] = [
  { id: 'short', label: '짧게', pages: '5-8p' },
  { id: 'default', label: '기본값', pages: '10-15p' },
  { id: 'detailed', label: '상세', pages: '20-30p' },
];

export default function SlideGeneratorModal({ onClose, selectedDocs }: Props) {
  const { currentProject } = useAppStore();
  const [format, setFormat] = useState<Format>('presentation');
  const [length, setLength] = useState<Length>('default');
  const [description, setDescription] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [slides, setSlides] = useState<any[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [step, setStep] = useState<'config' | 'planning' | 'preview'>('config');
  const [useMckinsey, setUseMckinsey] = useState(false);
  const [mode, setMode] = useState<DeckMode>('teaser');
  // PR4: 모드별 페이지 수 슬라이더 (Teaser 5~15, IM 20~50)
  const [teaserPages, setTeaserPages] = useState(10);
  const [imPages, setImPages] = useState(30);
  const targetPages = mode === 'teaser' ? teaserPages : imPages;

  // Planning state (Phase 0 인터랙티브 플래닝)
  const [plan, setPlan] = useState<DeckPlan | null>(null);
  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [feedback, setFeedback] = useState('');
  const [planLoading, setPlanLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // PR7: 페이지별 피드백 drawer
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [slideFeedback, setSlideFeedback] = useState('');
  const [slideRegen, setSlideRegen] = useState(false);
  const [revisionsByIdx, setRevisionsByIdx] = useState<Record<number, SlideRevision[]>>({});

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chat, planLoading]);

  const lengthGuide = LENGTH_OPTIONS.find(l => l.id === length)?.pages || '10-15p';

  // 사용자 목적 1줄 — config 의 description + 모드·페이지수 메타를 합침
  const buildUserGoal = useCallback(() => {
    const modeLabel = mode === 'teaser'
      ? `Teaser 모드 (핵심만, 정확히 ${teaserPages}p)`
      : `IM 모드 (정밀 분석, 약 ${imPages}p, Q&A로 목차 다듬기)`;
    return [
      description || (mode === 'teaser' ? 'Deal Teaser' : 'Information Memorandum'),
      `유형: ${modeLabel}`,
      `형식: ${format === 'detailed' ? '자세한 자료 (보고서형)' : '발표자 슬라이드 (시각적)'}`,
    ].join('\n');
  }, [description, format, mode, teaserPages, imPages]);

  // ── Phase 0: 인터랙티브 플래닝 시작 ──
  const startPlanning = useCallback(async () => {
    if (!currentProject) { setError('프로젝트를 먼저 선택하세요'); return; }
    setError('');
    setStep('planning');
    setChat([{ role: 'user', text: buildUserGoal() }]);
    setPlan(null);
    setPlanLoading(true);
    try {
      const r = await api.pptPlan({
        project_name: currentProject,
        selected_docs: selectedDocs,
        user_goal: buildUserGoal(),
        mode, target_pages: targetPages,
      });
      setPlan(r.plan as DeckPlan);
      setChat(prev => [...prev, { role: 'assistant', text: r.message || '제안한 플랜을 확인해주세요.' }]);
    } catch (e: any) {
      setError(`플래닝 실패: ${e?.message || e}`);
    } finally {
      setPlanLoading(false);
    }
  }, [currentProject, selectedDocs, buildUserGoal]);

  // ── 사용자 피드백으로 플랜 갱신 ──
  const sendFeedback = useCallback(async () => {
    const fb = feedback.trim();
    if (!fb || !currentProject || !plan) return;
    setChat(prev => [...prev, { role: 'user', text: fb }]);
    setFeedback('');
    setPlanLoading(true);
    try {
      const r = await api.pptPlan({
        project_name: currentProject,
        selected_docs: selectedDocs,
        user_goal: buildUserGoal(),
        prior_plan: plan,
        user_feedback: fb,
        mode, target_pages: targetPages,
      });
      setPlan(r.plan as DeckPlan);
      setChat(prev => [...prev, { role: 'assistant', text: r.message || '플랜을 갱신했습니다.' }]);
    } catch (e: any) {
      setChat(prev => [...prev, { role: 'assistant', text: `오류: ${e?.message || e}` }]);
    } finally {
      setPlanLoading(false);
    }
  }, [feedback, currentProject, plan, selectedDocs, buildUserGoal]);

  // ── Phase 1+2: 확정된 플랜 → 슬라이드 본문 생성 ──
  const confirmPlan = useCallback(async () => {
    if (!currentProject || !plan) return;
    // plan(planner 형식) → outline(slidesFromOutline 입력 형식) 변환
    const outline = {
      sections: (plan.sections || []).map(s => ({
        title: s.title,
        slides: (s.slides || []).map(sl => ({
          title: sl.title,
          slide_type: sl.type_hint || 'two_column',
          plan: sl.purpose || s.key_message || '',
        })),
      })),
    };
    setGenerating(true);
    setError('');
    setSlides([]);
    try {
      const { task_id } = await api.slidesFromOutline({
        outline,
        project_name: currentProject,
        selected_docs: selectedDocs,
        context_text: buildUserGoal(),
      });
      const poll = async () => {
        try {
          const status = await api.getTaskStatus(task_id);
          if (status.status === 'complete') {
            const raw = typeof status.result === 'string' ? JSON.parse(status.result) : status.result;
            const parsed = raw?.slides || raw || [];
            setSlides(Array.isArray(parsed) ? parsed : []);
            setStep('preview');
            setGenerating(false);
          } else if (status.status === 'error') {
            setError(status.error || '생성 오류');
            setGenerating(false);
          } else {
            setTimeout(poll, 2000);
          }
        } catch { setGenerating(false); }
      };
      poll();
    } catch (err: any) {
      setError(err.message);
      setGenerating(false);
    }
  }, [currentProject, plan, selectedDocs, buildUserGoal]);

  const handleGenerate = startPlanning;

  // ── PR3: 플랜 직접 편집 헬퍼 (LLM 거치지 않고 즉시 반영) ──
  const updatePlan = useCallback((mut: (p: DeckPlan) => DeckPlan) => {
    setPlan(prev => prev ? mut(JSON.parse(JSON.stringify(prev))) : prev);
  }, []);

  const updateSlide = useCallback((sIdx: number, slIdx: number, patch: Partial<PlanSlide>) => {
    updatePlan(p => {
      const sl = p.sections[sIdx]?.slides[slIdx];
      if (sl) Object.assign(sl, patch);
      return p;
    });
  }, [updatePlan]);

  const removeSlide = useCallback((sIdx: number, slIdx: number) => {
    updatePlan(p => {
      const sec = p.sections[sIdx];
      if (sec) {
        sec.slides.splice(slIdx, 1);
        sec.slide_count = sec.slides.length;
      }
      return p;
    });
  }, [updatePlan]);

  const moveSlide = useCallback((sIdx: number, slIdx: number, dir: -1 | 1) => {
    updatePlan(p => {
      const arr = p.sections[sIdx]?.slides;
      if (!arr) return p;
      const j = slIdx + dir;
      if (j < 0 || j >= arr.length) return p;
      [arr[slIdx], arr[j]] = [arr[j], arr[slIdx]];
      return p;
    });
  }, [updatePlan]);

  const addSlide = useCallback((sIdx: number) => {
    updatePlan(p => {
      const sec = p.sections[sIdx];
      if (sec) {
        sec.slides.push({ title: '새 슬라이드', type_hint: 'two_column', purpose: '' });
        sec.slide_count = sec.slides.length;
      }
      return p;
    });
  }, [updatePlan]);

  const removeSection = useCallback((sIdx: number) => {
    if (!confirm('섹션 전체를 삭제하시겠습니까?')) return;
    updatePlan(p => { p.sections.splice(sIdx, 1); return p; });
  }, [updatePlan]);

  const moveSection = useCallback((sIdx: number, dir: -1 | 1) => {
    updatePlan(p => {
      const j = sIdx + dir;
      if (j < 0 || j >= p.sections.length) return p;
      [p.sections[sIdx], p.sections[j]] = [p.sections[j], p.sections[sIdx]];
      return p;
    });
  }, [updatePlan]);

  const addSection = useCallback(() => {
    updatePlan(p => {
      p.sections.push({ title: '새 섹션', key_message: '', slide_count: 0, slides: [] });
      return p;
    });
  }, [updatePlan]);

  // ── PR7: 페이지별 피드백 → slideRegenerate → 슬라이드 교체 + 이력 저장 ──
  const submitSlideFeedback = useCallback(async () => {
    const fb = slideFeedback.trim();
    if (!fb) return;
    const cur = slides[selectedIdx];
    if (!cur) return;
    setSlideRegen(true);
    try {
      const { task_id } = await api.slideRegenerate({
        current_slide: cur,
        prev_slide: slides[selectedIdx - 1],
        next_slide: slides[selectedIdx + 1],
        instruction: fb,
      });
      const poll = async (): Promise<any> => {
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          const raw = typeof status.result === 'string' ? JSON.parse(status.result) : status.result;
          // 결과는 { slide: {...} } 또는 단일 dict 형태
          return raw?.slide || raw;
        } else if (status.status === 'error') {
          throw new Error(status.error || '재생성 오류');
        }
        await new Promise(r => setTimeout(r, 2000));
        return poll();
      };
      const newSlide = await poll();
      if (newSlide) {
        const idx = selectedIdx;
        setRevisionsByIdx(prev => ({
          ...prev,
          [idx]: [...(prev[idx] || []), {
            feedback: fb, prevSlide: cur, newSlide, at: new Date().toISOString(),
          }],
        }));
        setSlides(prev => prev.map((s, i) => i === idx ? newSlide : s));
        setSlideFeedback('');
      }
    } catch (e: any) {
      setError(`재생성 실패: ${e?.message || e}`);
    } finally { setSlideRegen(false); }
  }, [slideFeedback, slides, selectedIdx]);

  const restoreRevision = useCallback((idx: number, revIdx: number) => {
    if (!confirm('이 버전으로 되돌리시겠습니까?\n현재 버전도 이력에 남습니다.')) return;
    const revs = revisionsByIdx[idx] || [];
    const target = revs[revIdx];
    if (!target) return;
    const cur = slides[idx];
    setRevisionsByIdx(prev => ({
      ...prev,
      [idx]: [...revs, {
        feedback: '(되돌리기 전 버전 자동 보관)',
        prevSlide: cur, newSlide: target.prevSlide,
        at: new Date().toISOString(),
      }],
    }));
    setSlides(prev => prev.map((s, i) => i === idx ? target.prevSlide : s));
  }, [revisionsByIdx, slides]);

  const handleDownload = useCallback(async () => {
    try {
      const hasElements = slides.some((s: any) => s.elements);
      const deckJson = hasElements
        ? { deck_title: currentProject || '발표자료', slides }
        : {
            deck_title: currentProject || '발표자료',
            slides: slides.map((s, i) => ({
              title: s.title || `Slide ${i + 1}`,
              background: 'FFFFFF',
              elements: [
                { type: 'text', x: 0.5, y: 0.3, w: 9, h: 0.5, text: s.title || '', fontSize: 16, bold: true, color: '1B2A4A' },
                { type: 'text', x: 0.5, y: 1.0, w: 9, h: 4, text: JSON.stringify(s, null, 2), fontSize: 9, color: '2D2D2D' },
              ],
            })),
          };
      const blob = await api.createIbPptx(deckJson, { useMckinsey });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = generateFilename('발표자료', 'pptx', currentProject);
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(`다운로드 실패: ${err.message}`);
    }
  }, [slides, currentProject]);

  // ── 설정 화면 ──
  if (step === 'config') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/40" onClick={onClose} />
        <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
          {/* 헤더 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <span className="text-lg">📊</span>
              <span className="font-bold text-slate-800">슬라이드 자료 맞춤설정</span>
            </div>
            <button onClick={onClose} className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>

          <div className="p-6 space-y-6">
            {/* 모드 — Teaser vs IM */}
            <div>
              <div className="text-sm font-semibold text-slate-700 mb-3">덱 유형</div>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => setMode('teaser')}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${mode === 'teaser' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-slate-800">🎯 Teaser</span>
                    {mode === 'teaser' && <span className="text-blue-500">✓</span>}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">10p 내외 빠른 자료 — 핵심만, 한 번에 마무리</p>
                </button>
                <button onClick={() => setMode('im')}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${mode === 'im' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-slate-800">📚 IM</span>
                    {mode === 'im' && <span className="text-blue-500">✓</span>}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">30p+ 정밀 분석 — Q&A로 목차 다듬기</p>
                </button>
              </div>
            </div>

            {/* 페이지 수 슬라이더 (모드별 범위 다름) */}
            <div>
              <div className="flex items-baseline justify-between mb-2">
                <div className="text-sm font-semibold text-slate-700">목표 페이지 수</div>
                <div className="text-2xl font-bold text-blue-600 tabular-nums">{targetPages}<span className="text-sm font-medium text-slate-400 ml-1">p</span></div>
              </div>
              {mode === 'teaser' ? (
                <input type="range" min={5} max={15} step={1} value={teaserPages}
                  onChange={e => setTeaserPages(parseInt(e.target.value))}
                  className="w-full accent-blue-600" />
              ) : (
                <input type="range" min={20} max={50} step={5} value={imPages}
                  onChange={e => setImPages(parseInt(e.target.value))}
                  className="w-full accent-blue-600" />
              )}
              <div className="flex justify-between text-[10px] text-slate-400 mt-0.5">
                <span>{mode === 'teaser' ? '5p' : '20p'}</span>
                <span>{mode === 'teaser' ? '15p' : '50p'}</span>
              </div>
            </div>

            {/* 형식 */}
            <div>
              <div className="text-sm font-semibold text-slate-700 mb-3">형식</div>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => setFormat('detailed')}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${format === 'detailed' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-slate-800">자세한 자료</span>
                    {format === 'detailed' && <span className="text-blue-500">✓</span>}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">전체 텍스트와 세부정보 포함</p>
                </button>
                <button onClick={() => setFormat('presentation')}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${format === 'presentation' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-slate-800">발표자 슬라이드</span>
                    {format === 'presentation' && <span className="text-blue-500">✓</span>}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">핵심 시각 위주로 깔끔하게</p>
                </button>
              </div>
            </div>

            {/* 설명 */}
            <div>
              <div className="text-sm font-semibold text-slate-700 mb-2">만들려는 슬라이드 자료에 대한 설명</div>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="예: 10p 정도 Deal Teaser, 재무 분석 중심으로"
                rows={3}
                className="w-full px-4 py-3 border-2 border-slate-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            {/* McKinsey 스타일 토글 */}
            <div>
              <label className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
                <input type="checkbox" checked={useMckinsey} onChange={e => setUseMckinsey(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-blue-600" />
                <div className="flex-1">
                  <div className="text-sm font-semibold text-slate-700">McKinsey 스타일로 빌드 (베타)</div>
                  <p className="text-[11px] text-slate-500 leading-relaxed mt-0.5">
                    네이비/그레이 톤의 50종 템플릿 (BCG matrix · KPI dashboard · 차트 · 타임라인 등).
                    매핑 실패한 슬라이드는 기존 빌더로 fallback.
                  </p>
                </div>
              </label>
            </div>

            {/* 에러 */}
            {error && (
              <div className="px-4 py-3 bg-red-50 text-red-600 text-sm rounded-xl">{error}</div>
            )}
          </div>

          {/* 하단 */}
          <div className="flex justify-end px-6 py-4 border-t border-slate-200">
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-6 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 disabled:bg-blue-300 transition-colors"
            >
              {generating ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  플래닝 중...
                </span>
              ) : '플래닝 시작 →'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── 인터랙티브 플래닝 화면 ──
  if (step === 'planning') {
    const totalSlides = plan?.estimated_total_slides
      ?? (plan?.sections || []).reduce((acc, s) => acc + (s.slide_count || s.slides?.length || 0), 0);
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-white">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={() => setStep('config')}
              disabled={planLoading || generating}
              className="text-slate-400 hover:text-slate-600 disabled:opacity-30">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
            </button>
            <span className="font-bold text-slate-800">
              {mode === 'teaser' ? '🎯 Teaser 플래닝' : '📚 IM 플래닝 (Q&A)'}
            </span>
            {plan && (
              <span className="text-xs text-slate-500">
                {plan.title || '(제목 미정)'} · 약 {totalSlides}장 · {plan.audience || '청중 미정'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={confirmPlan}
              disabled={!plan || planLoading || generating}
              className="px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-700 disabled:bg-emerald-300">
              {generating ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  슬라이드 생성중…
                </span>
              ) : '✅ 플랜 확정 → 슬라이드 만들기'}
            </button>
            <button onClick={onClose} className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>

        {/* Body: left = plan card, right = chat */}
        <div className="flex flex-1 overflow-hidden">
          {/* Plan card */}
          <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
            {!plan && planLoading && (
              <div className="flex items-center justify-center h-full text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  자료를 분석하고 플랜을 작성하는 중…
                </div>
              </div>
            )}
            {plan && (
              <div className="max-w-3xl mx-auto space-y-3">
                {plan.tone && (
                  <div className="text-[11px] text-slate-500 italic">톤·스타일: {plan.tone}</div>
                )}
                {(plan.sections || []).map((sec, i) => (
                  <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm group/sec">
                    <div className="flex items-center gap-2 mb-1">
                      <input value={sec.title}
                        onChange={e => updatePlan(p => { p.sections[i].title = e.target.value; return p; })}
                        className="flex-1 text-sm font-bold text-slate-800 bg-transparent outline-none focus:bg-slate-50 rounded px-1 -mx-1" />
                      <div className="text-[11px] text-slate-400">{sec.slides?.length || 0}장</div>
                      <div className="opacity-0 group-hover/sec:opacity-100 flex items-center gap-0.5 transition-opacity">
                        <button onClick={() => moveSection(i, -1)} disabled={i === 0}
                          title="위로" className="px-1 text-slate-400 hover:text-slate-700 disabled:opacity-20">↑</button>
                        <button onClick={() => moveSection(i, 1)} disabled={i === plan.sections.length - 1}
                          title="아래로" className="px-1 text-slate-400 hover:text-slate-700 disabled:opacity-20">↓</button>
                        <button onClick={() => removeSection(i)} title="섹션 삭제"
                          className="px-1 text-slate-400 hover:text-red-600">🗑</button>
                      </div>
                    </div>
                    <input value={sec.key_message || ''}
                      onChange={e => updatePlan(p => { p.sections[i].key_message = e.target.value; return p; })}
                      placeholder="↳ 이 섹션의 핵심 메시지 (선택)"
                      className="w-full text-xs text-indigo-600 italic bg-transparent outline-none focus:bg-slate-50 rounded px-1 -mx-1 mb-2 placeholder:text-slate-300" />
                    <div className="space-y-1">
                      {(sec.slides || []).map((sl, j) => (
                        <div key={j} className="group/sl flex items-start gap-2 text-xs py-1 hover:bg-slate-50 rounded px-1 -mx-1">
                          <span className="text-slate-300 shrink-0 w-4 pt-1">{j + 1}.</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <input value={sl.title}
                                onChange={e => updateSlide(i, j, { title: e.target.value })}
                                className="flex-1 font-medium text-slate-700 bg-transparent outline-none focus:bg-white border border-transparent focus:border-slate-200 rounded px-1.5 py-0.5" />
                              <select value={sl.type_hint || 'two_column'}
                                onChange={e => updateSlide(i, j, { type_hint: e.target.value })}
                                className="text-[10px] px-1 py-0.5 bg-slate-100 text-slate-600 rounded border-0 focus:outline-none focus:ring-1 focus:ring-indigo-300 max-w-[140px]">
                                {['구조', '요약', '숫자', '비교', '매트릭스', '차트', '프로세스', '조직', '일반'].map(g => (
                                  <optgroup key={g} label={g}>
                                    {TYPE_HINT_OPTIONS.filter(o => o.group === g).map(o => (
                                      <option key={o.value} value={o.value}>{o.label}</option>
                                    ))}
                                  </optgroup>
                                ))}
                              </select>
                              <div className="opacity-0 group-hover/sl:opacity-100 flex gap-0.5 transition-opacity shrink-0">
                                <button onClick={() => moveSlide(i, j, -1)} disabled={j === 0}
                                  className="text-[10px] text-slate-400 hover:text-slate-700 disabled:opacity-20 px-1">↑</button>
                                <button onClick={() => moveSlide(i, j, 1)} disabled={j === sec.slides.length - 1}
                                  className="text-[10px] text-slate-400 hover:text-slate-700 disabled:opacity-20 px-1">↓</button>
                                <button onClick={() => removeSlide(i, j)}
                                  className="text-[10px] text-slate-400 hover:text-red-600 px-1">×</button>
                              </div>
                            </div>
                            <input value={sl.purpose || ''}
                              onChange={e => updateSlide(i, j, { purpose: e.target.value })}
                              placeholder="이 슬라이드가 보여줄 것 (선택)"
                              className="w-full text-[11px] text-slate-500 bg-transparent outline-none focus:bg-white border border-transparent focus:border-slate-200 rounded px-1.5 py-0.5 mt-0.5 placeholder:text-slate-300" />
                          </div>
                        </div>
                      ))}
                      <button onClick={() => addSlide(i)}
                        className="w-full text-[11px] text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded py-1.5 border border-dashed border-slate-200 hover:border-indigo-300">
                        + 슬라이드 추가
                      </button>
                    </div>
                  </div>
                ))}
                <button onClick={addSection}
                  className="w-full text-xs text-slate-400 hover:text-indigo-600 hover:bg-white hover:border-indigo-300 rounded-xl py-3 border border-dashed border-slate-300">
                  + 섹션 추가
                </button>
              </div>
            )}
          </div>

          {/* Chat */}
          <div className="w-96 shrink-0 border-l border-slate-200 flex flex-col bg-white">
            <div className="px-4 py-2.5 border-b border-slate-200 text-xs font-semibold text-slate-600 flex items-center justify-between">
              <span>💬 {mode === 'teaser' ? '필요하면 한 줄로 수정' : '자유롭게 대화'}</span>
              {mode === 'teaser' && plan && (
                <span className="text-[10px] text-emerald-600 font-normal">→ 바로 [확정] 가능</span>
              )}
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
              {chat.map((m, i) => (
                <div key={i}
                  className={`max-w-[90%] rounded-2xl px-3 py-2 text-[13px] leading-relaxed ${
                    m.role === 'user'
                      ? 'ml-auto bg-blue-500 text-white'
                      : 'mr-auto bg-slate-100 text-slate-800'
                  }`}>
                  {m.text}
                </div>
              ))}
              {planLoading && (
                <div className="mr-auto bg-slate-100 text-slate-500 rounded-2xl px-3 py-2 text-xs flex items-center gap-2">
                  <div className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                  생각하는 중…
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="border-t border-slate-200 p-2">
              <div className="flex flex-wrap gap-1 mb-2">
                {(mode === 'teaser'
                  ? ['더 짧게', '시장 분석 강조', 'Investment Highlights 추가', '재무 페이지 추가']
                  : ['Risk 섹션 강화', 'Valuation 상세화', 'Cap Table 추가', 'Exit 시나리오 보강', '경쟁사 비교 추가']
                ).map(s => (
                  <button key={s} onClick={() => setFeedback(s)}
                    className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full hover:bg-slate-200">
                    {s}
                  </button>
                ))}
              </div>
              <textarea value={feedback}
                onChange={e => setFeedback(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); sendFeedback(); }
                }}
                placeholder="수정 지시를 입력하세요 (Ctrl+Enter 전송)"
                rows={2}
                disabled={planLoading || !plan}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-blue-400 resize-none disabled:bg-slate-50" />
              <div className="flex justify-end mt-1.5">
                <button onClick={sendFeedback}
                  disabled={!feedback.trim() || planLoading || !plan}
                  className="px-3 py-1 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-40">
                  보내기
                </button>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="px-5 py-2 bg-red-50 text-red-600 text-sm border-t border-red-100">{error}</div>
        )}
      </div>
    );
  }

  // ── 미리보기 화면 ──
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => setStep('config')} className="text-slate-400 hover:text-slate-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <span className="font-bold text-slate-800">슬라이드 미리보기</span>
          <span className="text-xs text-slate-400">{slides.length}장</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleDownload}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors">
            PPTX 다운로드
          </button>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
      </div>

      {/* 콘텐츠 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 슬라이드 리스트 */}
        <div className="w-48 shrink-0 border-r border-slate-200 overflow-y-auto p-2 space-y-2">
          {slides.map((slide, i) => {
            const revCount = (revisionsByIdx[i] || []).length;
            return (
              <div key={i} className="relative">
                <div className="flex items-center justify-between mb-0.5 pl-1">
                  <span className="text-[10px] text-slate-400">{i + 1}</span>
                  {revCount > 0 && (
                    <button onClick={e => { e.stopPropagation(); setSelectedIdx(i); setFeedbackOpen(true); }}
                      title={`수정 이력 ${revCount}회 — 드로어에서 보기`}
                      className="text-[9px] px-1 py-0.5 bg-amber-100 text-amber-700 rounded hover:bg-amber-200">
                      ✏️{revCount}
                    </button>
                  )}
                </div>
                <SlidePreview slide={slide} selected={i === selectedIdx} onClick={() => setSelectedIdx(i)} width={160} />
              </div>
            );
          })}
        </div>
        {/* 메인 미리보기 */}
        <div className="flex-1 flex items-center justify-center bg-slate-100 p-8 relative">
          {slides[selectedIdx] && (
            <SlidePreview slide={slides[selectedIdx]} width={Math.min(800, window.innerWidth - 300 - (feedbackOpen ? 380 : 0))} />
          )}
          {/* [✏️ 피드백] 토글 */}
          <button onClick={() => setFeedbackOpen(v => !v)}
            title="이 슬라이드에 피드백"
            className={`absolute top-4 right-4 px-3 py-2 text-xs rounded-lg shadow-md transition-all ${
              feedbackOpen ? 'bg-amber-500 text-white' : 'bg-white text-slate-700 border border-slate-200 hover:bg-amber-50'
            }`}>
            ✏️ 피드백
          </button>
        </div>

        {/* PR7: 페이지별 피드백 drawer (우측) */}
        {feedbackOpen && (
          <div className="w-[380px] shrink-0 border-l border-slate-200 flex flex-col bg-white">
            <div className="px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-700">
                ✏️ 슬라이드 {selectedIdx + 1} 피드백
              </div>
              <button onClick={() => setFeedbackOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-sm">✕</button>
            </div>
            {/* 이력 (있으면 상단에 collapsible) */}
            {(revisionsByIdx[selectedIdx] || []).length > 0 && (
              <div className="border-b border-slate-200 max-h-48 overflow-y-auto">
                <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-500 sticky top-0 bg-white">
                  수정 이력 ({revisionsByIdx[selectedIdx].length}회)
                </div>
                {(revisionsByIdx[selectedIdx] || []).map((rev, ri) => (
                  <div key={ri} className="group px-3 py-1.5 border-t border-slate-100 hover:bg-slate-50">
                    <div className="text-[11px] text-slate-700 line-clamp-2">{rev.feedback}</div>
                    <div className="flex items-center justify-between mt-0.5">
                      <span className="text-[9px] text-slate-400">
                        {new Date(rev.at).toLocaleString('ko', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <button onClick={() => restoreRevision(selectedIdx, ri)}
                        className="text-[10px] text-amber-600 hover:text-amber-800 opacity-0 group-hover:opacity-100">
                        ↶ 이전 버전으로
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {/* 입력 영역 */}
            <div className="flex-1 flex flex-col p-3 space-y-2">
              <div className="text-[11px] text-slate-500 leading-relaxed">
                예: "EBITDA margin 추가", "테이블을 차트로 바꿔줘",
                "표지를 더 임팩트 있게"
              </div>
              <div className="flex flex-wrap gap-1">
                {['더 간결하게', '데이터 추가', '차트로 변환', '제목 다시'].map(s => (
                  <button key={s} onClick={() => setSlideFeedback(s)}
                    className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full hover:bg-amber-50">
                    {s}
                  </button>
                ))}
              </div>
              <textarea value={slideFeedback}
                onChange={e => setSlideFeedback(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submitSlideFeedback(); }
                }}
                placeholder="이 슬라이드를 어떻게 바꿀까요? (Ctrl+Enter 전송)"
                rows={4}
                disabled={slideRegen}
                className="flex-1 px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-amber-400 resize-none disabled:bg-slate-50" />
              <button onClick={submitSlideFeedback}
                disabled={!slideFeedback.trim() || slideRegen}
                className="px-3 py-2 text-xs bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-40">
                {slideRegen ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    재생성 중…
                  </span>
                ) : '🔁 이 페이지만 다시 만들기'}
              </button>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="px-5 py-2 bg-red-50 text-red-600 text-sm border-t border-red-100">{error}</div>
      )}
    </div>
  );
}
