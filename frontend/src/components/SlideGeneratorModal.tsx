/**
 * SlideGeneratorModal — NotebookLM 스타일 슬라이드 맞춤설정 모달
 * 형식/템플릿/길이 선택 → 설명 입력 → 생성 → 미리보기 → 다운로드
 */
import { useState, useCallback } from 'react';
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

const TEMPLATES = [
  { id: 'free', label: '자유양식', icon: '📝' },
  { id: 'investment', label: '투심보고서', icon: '💰' },
  { id: 'teaser', label: 'Teaser', icon: '🎯' },
  { id: 'dd_report', label: 'DD 보고서', icon: '🔬' },
  { id: 'im', label: 'IM', icon: '📖' },
  { id: 'term_sheet', label: 'Term Sheet', icon: '📑' },
];

const LENGTH_OPTIONS: { id: Length; label: string; pages: string }[] = [
  { id: 'short', label: '짧게', pages: '5-8p' },
  { id: 'default', label: '기본값', pages: '10-15p' },
  { id: 'detailed', label: '상세', pages: '20-30p' },
];

export default function SlideGeneratorModal({ onClose, selectedDocs }: Props) {
  const { currentProject } = useAppStore();
  const [format, setFormat] = useState<Format>('presentation');
  const [template, setTemplate] = useState('free');
  const [length, setLength] = useState<Length>('default');
  const [description, setDescription] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [slides, setSlides] = useState<any[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [step, setStep] = useState<'config' | 'preview'>('config');

  const lengthGuide = LENGTH_OPTIONS.find(l => l.id === length)?.pages || '10-15p';
  const templateLabel = TEMPLATES.find(t => t.id === template)?.label || '자유양식';

  const handleGenerate = useCallback(async () => {
    if (!currentProject) { setError('프로젝트를 먼저 선택하세요'); return; }
    setGenerating(true);
    setError('');
    setSlides([]);

    const query = [
      description || `${templateLabel} 발표자료`,
      `형식: ${format === 'detailed' ? '자세한 자료 (보고서형)' : '발표자 슬라이드 (시각적)'}`,
      `템플릿: ${templateLabel}`,
      `길이: ${lengthGuide}`,
    ].join('\n');

    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'slide_json',
        kwargs: {
          project_name: currentProject,
          selected_docs: selectedDocs,
          context_text: query,
        },
      });

      // Poll
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
  }, [currentProject, description, format, template, length, selectedDocs, templateLabel, lengthGuide]);

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

            {/* 템플릿 */}
            <div>
              <div className="text-sm font-semibold text-slate-700 mb-3">템플릿</div>
              <div className="grid grid-cols-3 gap-2">
                {TEMPLATES.map(t => (
                  <button key={t.id} onClick={() => setTemplate(t.id)}
                    className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-left transition-all ${template === t.id ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 hover:border-slate-300 text-slate-600'}`}>
                    <span>{t.icon}</span>
                    <span className="text-xs font-medium">{t.label}</span>
                  </button>
                ))}
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
                  생성 중...
                </span>
              ) : '생성'}
            </button>
          </div>
        </div>
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
