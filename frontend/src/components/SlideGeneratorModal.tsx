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

interface PlanSlide { title: string; type_hint?: string; purpose?: string }
interface PlanSection { title: string; key_message?: string; slide_count?: number; slides: PlanSlide[] }
interface DeckPlan { title?: string; audience?: string; tone?: string; estimated_total_slides?: number; sections: PlanSection[] }
interface ChatTurn { role: 'assistant' | 'user'; text: string }

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

  // Planning state (Phase 0 인터랙티브 플래닝)
  const [plan, setPlan] = useState<DeckPlan | null>(null);
  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [feedback, setFeedback] = useState('');
  const [planLoading, setPlanLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chat, planLoading]);

  const lengthGuide = LENGTH_OPTIONS.find(l => l.id === length)?.pages || '10-15p';

  // 사용자 목적 1줄 — config 의 description + 형식·길이 메타를 합침
  const buildUserGoal = useCallback(() => {
    return [
      description || '발표자료',
      `형식: ${format === 'detailed' ? '자세한 자료 (보고서형)' : '발표자 슬라이드 (시각적)'}`,
      `길이: ${lengthGuide}`,
    ].join('\n');
  }, [description, format, lengthGuide]);

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
      const blob = await api.createIbPptx(deckJson);
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
                  <p className="text-xs text-slate-500 leading-relaxed">전체 텍스트와 세부정보가 포함된 포괄적인 자료</p>
                </button>
                <button onClick={() => setFormat('presentation')}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${format === 'presentation' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-slate-800">발표자 슬라이드</span>
                    {format === 'presentation' && <span className="text-blue-500">✓</span>}
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">핵심 내용을 담은 깔끔하고 시각적인 슬라이드</p>
                </button>
              </div>
            </div>

            {/* 길이 */}
            <div>
              <div className="text-sm font-semibold text-slate-700 mb-3">길이</div>
              <div className="flex gap-2">
                {LENGTH_OPTIONS.map(l => (
                  <button key={l.id} onClick={() => setLength(l.id)}
                    className={`flex-1 py-2.5 rounded-xl border text-center transition-all ${length === l.id ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 hover:border-slate-300 text-slate-600'}`}>
                    <div className="text-sm font-medium">{l.label}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{l.pages}</div>
                  </button>
                ))}
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
            <span className="font-bold text-slate-800">📋 슬라이드 플래닝</span>
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
                  <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                    <div className="flex items-baseline justify-between mb-1">
                      <div className="text-sm font-bold text-slate-800">{sec.title}</div>
                      <div className="text-[11px] text-slate-400">{sec.slide_count || sec.slides?.length || 0}장</div>
                    </div>
                    {sec.key_message && (
                      <div className="text-xs text-indigo-600 mb-2 italic">↳ {sec.key_message}</div>
                    )}
                    <div className="space-y-1">
                      {(sec.slides || []).map((sl, j) => (
                        <div key={j} className="flex items-start gap-2 text-xs text-slate-600 py-0.5">
                          <span className="text-slate-300 shrink-0 w-4">{j + 1}.</span>
                          <div className="flex-1">
                            <span className="font-medium text-slate-700">{sl.title}</span>
                            {sl.type_hint && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">{sl.type_hint}</span>}
                            {sl.purpose && <div className="text-[11px] text-slate-400 mt-0.5">{sl.purpose}</div>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Chat */}
          <div className="w-96 shrink-0 border-l border-slate-200 flex flex-col bg-white">
            <div className="px-4 py-2.5 border-b border-slate-200 text-xs font-semibold text-slate-600">
              💬 대화로 플랜 다듬기
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
                {['3장은 빼줘', '재무 슬라이드 추가', '더 짧게 (15장 이하)', 'Risk 섹션 강화'].map(s => (
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
          {slides.map((slide, i) => (
            <div key={i}>
              <div className="text-[10px] text-slate-400 mb-0.5 pl-1">{i + 1}</div>
              <SlidePreview slide={slide} selected={i === selectedIdx} onClick={() => setSelectedIdx(i)} width={160} />
            </div>
          ))}
        </div>
        {/* 메인 미리보기 */}
        <div className="flex-1 flex items-center justify-center bg-slate-100 p-8">
          {slides[selectedIdx] && (
            <SlidePreview slide={slides[selectedIdx]} width={Math.min(800, window.innerWidth - 300)} />
          )}
        </div>
      </div>

      {error && (
        <div className="px-5 py-2 bg-red-50 text-red-600 text-sm border-t border-red-100">{error}</div>
      )}
    </div>
  );
}
