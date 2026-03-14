import { useRef, useState, useCallback } from 'react';
import { api } from '../api/client';
import SlidePreview from '../components/SlidePreview';
import { generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';

interface SlideData {
  slide_type?: string;
  type?: string;
  title?: string;
  subtitle?: string;
  layout_hint?: string;
  elements?: any[];
  left?: any;
  right?: any;
  summary?: string;
}

export default function PptToolsPage() {
  const { currentProject } = useAppStore();
  const [tab, setTab] = useState<'generate' | 'update'>('generate');

  // Generate tab state
  const [context, setContext] = useState('');
  const [slides, setSlides] = useState<SlideData[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const cancelRef = useRef(false);

  // Edit panel
  const [editInstruction, setEditInstruction] = useState('');
  const [regenerating, setRegenerating] = useState(false);

  // Update tab
  const [pptxFile, setPptxFile] = useState<File | null>(null);
  const [updateStatus, setUpdateStatus] = useState('');
  const [updating, setUpdating] = useState(false);
  const updateAbortRef = useRef<AbortController | null>(null);

  // --- Generate ---
  const handleGenerate = useCallback(async () => {
    if (!currentProject) {
      setError('프로젝트를 먼저 선택하세요.');
      return;
    }
    setGenerating(true);
    setError('');
    setSlides([]);
    setSelectedIdx(0);
    cancelRef.current = false;

    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'slide_json',
        project_name: currentProject,
        kwargs: { file_context: context, context_text: context },
      });

      const poll = async () => {
        if (cancelRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          try {
            const raw = typeof status.result === 'string' ? JSON.parse(status.result) : status.result;
            const parsed: SlideData[] = raw.slides || raw;
            setSlides(parsed);
            setSelectedIdx(0);
          } catch {
            setError('JSON 파싱 실패');
          }
          setGenerating(false);
        } else if (status.status === 'error') {
          setError(status.error || '생성 오류');
          setGenerating(false);
        } else {
          setTimeout(poll, 1200);
        }
      };
      poll();
    } catch (err: any) {
      setError(err.message);
      setGenerating(false);
    }
  }, [currentProject, context]);

  // --- Download PPTX ---
  const handleDownload = useCallback(async () => {
    try {
      const blob = await api.createPptx({ slides });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = generateFilename('발표자료', 'pptx', currentProject);
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(`PPTX 다운로드 실패: ${err.message}`);
    }
  }, [slides, currentProject]);

  // --- Slide Regenerate ---
  const handleRegenerate = useCallback(async () => {
    if (!editInstruction.trim() || slides.length === 0) return;
    setRegenerating(true);
    setError('');

    const current = slides[selectedIdx];
    const prev = selectedIdx > 0 ? slides[selectedIdx - 1] : null;
    const next = selectedIdx < slides.length - 1 ? slides[selectedIdx + 1] : null;

    try {
      const { task_id } = await api.slideRegenerate({
        current_slide: current,
        prev_slide: prev,
        next_slide: next,
        instruction: editInstruction,
      });

      const poll = async () => {
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          try {
            const newSlide = typeof status.result === 'string' ? JSON.parse(status.result) : status.result;
            setSlides((prev) => {
              const copy = [...prev];
              copy[selectedIdx] = newSlide;
              return copy;
            });
            setEditInstruction('');
          } catch {
            setError('재생성 결과 파싱 실패');
          }
          setRegenerating(false);
        } else if (status.status === 'error') {
          setError(status.error || '재생성 오류');
          setRegenerating(false);
        } else {
          setTimeout(poll, 1000);
        }
      };
      poll();
    } catch (err: any) {
      setError(err.message);
      setRegenerating(false);
    }
  }, [slides, selectedIdx, editInstruction]);

  // --- Update PPTX History ---
  const handleUpdate = useCallback(async () => {
    if (!pptxFile) return;
    setUpdating(true);
    setUpdateStatus('');
    try {
      const blob = await api.updatePptxHistory(pptxFile);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = generateFilename('PPT업데이트', 'pptx', currentProject);
      a.click();
      URL.revokeObjectURL(url);
      setUpdateStatus('업데이트 완료! 파일이 다운로드됩니다.');
    } catch (err: any) {
      setUpdateStatus(`오류: ${err.message}`);
    }
    setUpdating(false);
  }, [pptxFile, currentProject]);

  const selectedSlide = slides[selectedIdx] || null;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">발표자료 (PPT)</h1>
      <p className="text-sm text-[#787774] mb-6">문서 기반 PPT 생성 및 투자이력 업데이트</p>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab('generate')}
          className={`px-4 py-2 text-sm rounded-lg ${tab === 'generate' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          PPT 생성
        </button>
        <button onClick={() => setTab('update')}
          className={`px-4 py-2 text-sm rounded-lg ${tab === 'update' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          투자이력 업데이트
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 text-red-700 text-sm rounded-lg">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-500 hover:text-red-800">X</button>
        </div>
      )}

      {tab === 'generate' && (
        <div>
          {/* Input area */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">발표 범위/지시사항</label>
            <textarea value={context} onChange={(e) => setContext(e.target.value)}
              placeholder="PPT에 포함할 범위, 강조할 내용, 특별 지시사항 (예: KPI 슬라이드 포함, 차트 강조 등)"
              rows={3}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none" />
          </div>

          {/* Generate / Stop */}
          {generating ? (
            <div className="flex gap-2 mb-4">
              <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center animate-pulse">
                슬라이드 구조 생성 중...
              </div>
              <button onClick={() => { cancelRef.current = true; setGenerating(false); }}
                className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
                중지
              </button>
            </div>
          ) : (
            <button onClick={handleGenerate} disabled={!currentProject}
              className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
              PPT 생성 ({currentProject || '프로젝트 미선택'})
            </button>
          )}

          {/* Slide workspace */}
          {slides.length > 0 && (
            <div className="flex gap-4">
              {/* Slide list (left) */}
              <div className="w-48 flex-shrink-0 space-y-2 max-h-[600px] overflow-y-auto pr-1">
                {slides.map((slide, i) => (
                  <div key={i} className="relative">
                    <div className="text-[10px] text-[#787774] mb-0.5 pl-1">
                      {i + 1}. {(slide.slide_type || slide.type || 'content')}
                    </div>
                    <SlidePreview
                      slide={slide}
                      selected={i === selectedIdx}
                      onClick={() => setSelectedIdx(i)}
                      width={176}
                    />
                  </div>
                ))}
              </div>

              {/* Preview + Edit (right) */}
              <div className="flex-1 min-w-0">
                {/* Large preview */}
                {selectedSlide && (
                  <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-sm font-semibold text-[#37352F]">
                        슬라이드 {selectedIdx + 1} / {slides.length}
                        {selectedSlide.layout_hint && (
                          <span className="ml-2 px-2 py-0.5 text-xs bg-[#EFF6FF] text-[#2383E2] rounded">
                            {selectedSlide.layout_hint}
                          </span>
                        )}
                      </div>
                      <button onClick={handleDownload}
                        className="px-3 py-1.5 text-xs bg-[#2383E2] text-white rounded-lg hover:bg-[#1b6ec2]">
                        PPTX 다운로드
                      </button>
                    </div>
                    <div className="flex justify-center">
                      <SlidePreview slide={selectedSlide} width={480} />
                    </div>
                  </div>
                )}

                {/* Edit panel */}
                {selectedSlide && (
                  <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
                    <div className="text-sm font-semibold text-[#37352F] mb-2">슬라이드 편집</div>
                    <div className="text-xs text-[#787774] mb-2">
                      선택한 슬라이드에 대한 수정 지시를 입력하면 AI가 해당 슬라이드만 재생성합니다.
                    </div>
                    <textarea
                      value={editInstruction}
                      onChange={(e) => setEditInstruction(e.target.value)}
                      placeholder="예: 차트를 추가해줘 / KPI 카드로 변경 / 내용을 간결하게 줄여줘"
                      rows={2}
                      className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none mb-2"
                    />
                    <button
                      onClick={handleRegenerate}
                      disabled={regenerating || !editInstruction.trim()}
                      className="w-full py-2 bg-[#37352F] text-white text-sm font-semibold rounded-xl hover:bg-[#2b2a28] disabled:bg-[#b0b0b0] transition-colors"
                    >
                      {regenerating ? '재생성 중...' : '이 슬라이드 재생성'}
                    </button>

                    {/* Slide JSON viewer */}
                    <details className="mt-3">
                      <summary className="text-xs text-[#787774] cursor-pointer hover:text-[#37352F]">
                        슬라이드 JSON 보기
                      </summary>
                      <pre className="mt-1 p-2 bg-[#F7F6F3] rounded text-[10px] max-h-48 overflow-auto whitespace-pre-wrap">
                        {JSON.stringify(selectedSlide, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'update' && (
        <div>
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">PPTX 파일</label>
            <label className="inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3]">
              PPTX 파일 선택
              <input type="file" accept=".pptx" onChange={(e) => setPptxFile(e.target.files?.[0] || null)} className="hidden" />
            </label>
            {pptxFile && <span className="ml-2 text-xs text-[#787774]">{pptxFile.name}</span>}
          </div>

          {updating ? (
            <div className="flex gap-2 mb-4">
              <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
                업데이트 중...
              </div>
              <button onClick={() => { updateAbortRef.current?.abort(); setUpdating(false); }}
                className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
                중지
              </button>
            </div>
          ) : (
            <button onClick={handleUpdate} disabled={!pptxFile}
              className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
              투자이력 업데이트
            </button>
          )}

          {updateStatus && (
            <div className={`px-4 py-3 rounded-lg text-sm ${updateStatus.startsWith('오류') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
              {updateStatus}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
