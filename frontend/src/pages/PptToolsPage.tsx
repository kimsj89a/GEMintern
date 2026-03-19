import { useRef, useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';
import { subscribeTask, unsubscribeTask } from '../api/ws';
import SlidePreview from '../components/SlidePreview';
import OutlineEditor from '../components/OutlineEditor';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';
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

  // Project docs
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [docsOpen, setDocsOpen] = useState(true);

  // Generate tab state
  const [context, setContext] = useState('');
  const [slides, setSlides] = useState<SlideData[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const cancelRef = useRef(false);

  // Outline editing
  const [outline, setOutline] = useState<any>(null);
  const [outlineGenerating, setOutlineGenerating] = useState(false);

  // Edit panel
  const [editInstruction, setEditInstruction] = useState('');
  const [regenerating, setRegenerating] = useState(false);

  // Upload to project
  const [uploading, setUploading] = useState(false);

  // Update tab
  const [pptxFile, setPptxFile] = useState<File | null>(null);
  const [updateStatus, setUpdateStatus] = useState('');
  const [updating, setUpdating] = useState(false);

  const loadDocs = useCallback(() => {
    if (!currentProject) { setTree({}); return; }
    api.getProjectDocs(currentProject)
      .then((data) => setTree(data.folder_tree || {}))
      .catch(() => setTree({}));
  }, [currentProject]);

  // Load project docs when project changes
  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleUploadFiles = useCallback(async (files: File[]) => {
    if (!currentProject || files.length === 0) {
      setError('프로젝트를 먼저 선택하세요.');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const result = await api.uploadFiles(currentProject, files);
      const count = Object.keys(result.parsed_texts || {}).length;
      const errCount = result.parse_errors?.length || 0;
      setError(errCount > 0 ? `${count}개 업로드, ${errCount}개 파싱 실패` : '');
      loadDocs();
    } catch (err: any) {
      setError(`업로드 실패: ${err.message}`);
    }
    setUploading(false);
  }, [currentProject, loadDocs]);

  const totalDocs = Object.values(tree).flat().length;

  // --- Outline Generation (Phase 1) ---
  const taskIdRef = useRef<string>('');

  const handleGenerateOutline = useCallback(async () => {
    if (!currentProject) {
      setError('사이드바에서 프로젝트를 먼저 선택하세요.');
      return;
    }
    if (totalDocs === 0) {
      setError('프로젝트에 문서가 없습니다. 프로젝트 페이지에서 문서를 업로드하세요.');
      return;
    }
    setOutlineGenerating(true);
    setError('');
    setOutline(null);
    setSlides([]);

    try {
      const { task_id } = await api.slideOutline({
        task_type: 'slide_outline',
        kwargs: {
          project_name: currentProject,
          selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
          context_text: context,
        },
      });

      const poll = async () => {
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          const result = typeof status.result === 'string' ? JSON.parse(status.result) : status.result;
          setOutline(result);
          setOutlineGenerating(false);
        } else if (status.status === 'error') {
          setError(status.error || '아웃라인 생성 오류');
          setOutlineGenerating(false);
        } else {
          setTimeout(poll, 2000);
        }
      };
      poll();
    } catch (err: any) {
      setError(err.message);
      setOutlineGenerating(false);
    }
  }, [currentProject, context, selectedDocs, totalDocs]);

  // --- Direct Generate (skip outline editing) ---
  const handleGenerate = useCallback(async () => {
    if (!currentProject) {
      setError('사이드바에서 프로젝트를 먼저 선택하세요.');
      return;
    }
    if (totalDocs === 0) {
      setError('프로젝트에 문서가 없습니다. 프로젝트 페이지에서 문서를 업로드하세요.');
      return;
    }
    setGenerating(true);
    setError('');
    setSlides([]);
    setSelectedIdx(0);
    setOutline(null);
    cancelRef.current = false;

    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'slide_json',
        kwargs: {
          project_name: currentProject,
          selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
          context_text: context,
        },
      });
      taskIdRef.current = task_id;

      // Subscribe to WebSocket for streaming slides
      subscribeTask(task_id, (msg) => {
        if (cancelRef.current) {
          unsubscribeTask(task_id);
          return;
        }
        if (msg.type === 'slide' && msg.slide) {
          setSlides((prev) => [...prev, msg.slide as SlideData]);
          setSelectedIdx((prev) => prev === 0 ? 0 : prev);
        } else if (msg.type === 'complete') {
          try {
            const raw = typeof msg.result === 'string' ? JSON.parse(msg.result) : msg.result;
            const parsed: SlideData[] = raw?.slides || raw || [];
            if (parsed.length > 0) setSlides(parsed);
          } catch { /* keep streamed slides */ }
          setGenerating(false);
          unsubscribeTask(task_id);
        } else if (msg.type === 'error') {
          setError(msg.error || '생성 오류');
          setGenerating(false);
          unsubscribeTask(task_id);
        }
      });

      // Fallback polling
      const pollFallback = async () => {
        if (cancelRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          try {
            const raw = typeof status.result === 'string' ? JSON.parse(status.result) : status.result;
            const parsed: SlideData[] = raw?.slides || raw || [];
            if (parsed.length > 0) setSlides(parsed);
          } catch { /* ignore */ }
          setGenerating(false);
          unsubscribeTask(task_id);
        } else if (status.status === 'error') {
          setError(status.error || '생성 오류');
          setGenerating(false);
          unsubscribeTask(task_id);
        } else {
          setTimeout(pollFallback, 3000);
        }
      };
      setTimeout(pollFallback, 5000);
    } catch (err: any) {
      setError(err.message);
      setGenerating(false);
    }
  }, [currentProject, context, selectedDocs, totalDocs]);

  // --- Generate from edited outline (Phase 2) ---
  const handleConfirmOutline = useCallback(async (editedOutline: any) => {
    setGenerating(true);
    setError('');
    setSlides([]);
    setSelectedIdx(0);
    setOutline(null);
    cancelRef.current = false;

    try {
      const { task_id } = await api.slidesFromOutline({
        outline: editedOutline,
        project_name: currentProject || '',
        selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
        context_text: context,
      });
      taskIdRef.current = task_id;

      subscribeTask(task_id, (msg) => {
        if (cancelRef.current) {
          unsubscribeTask(task_id);
          return;
        }
        if (msg.type === 'slide' && msg.slide) {
          setSlides((prev) => [...prev, msg.slide as SlideData]);
        } else if (msg.type === 'complete') {
          try {
            const raw = typeof msg.result === 'string' ? JSON.parse(msg.result) : msg.result;
            const parsed: SlideData[] = raw?.slides || raw || [];
            if (parsed.length > 0) setSlides(parsed);
          } catch { /* keep streamed slides */ }
          setGenerating(false);
          unsubscribeTask(task_id);
        } else if (msg.type === 'error') {
          setError(msg.error || '생성 오류');
          setGenerating(false);
          unsubscribeTask(task_id);
        }
      });

      const pollFallback = async () => {
        if (cancelRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          try {
            const raw = typeof status.result === 'string' ? JSON.parse(status.result) : status.result;
            const parsed: SlideData[] = raw?.slides || raw || [];
            if (parsed.length > 0) setSlides(parsed);
          } catch { /* ignore */ }
          setGenerating(false);
          unsubscribeTask(task_id);
        } else if (status.status === 'error') {
          setError(status.error || '생성 오류');
          setGenerating(false);
          unsubscribeTask(task_id);
        } else {
          setTimeout(pollFallback, 3000);
        }
      };
      setTimeout(pollFallback, 5000);
    } catch (err: any) {
      setError(err.message);
      setGenerating(false);
    }
  }, [currentProject, context, selectedDocs]);

  // --- Download PPTX (pptxgenjs IB 마스터 사용) ---
  const handleDownload = useCallback(async () => {
    try {
      // IB 아웃라인 포맷으로 변환하여 pptxgenjs 렌더링
      const deckJson = {
        deck_title: currentProject || '발표자료',
        subtitle: 'Investment Presentation',
        date: new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' }),
        confidential: true,
        slides: slides.map((s, i) => ({
          slide_number: i + 1,
          slide_type: s.slide_type || s.type || 'text_heavy',
          title: s.title || `Slide ${i + 1}`,
          subtitle: s.subtitle || '',
          content: s,
          speaker_notes: '',
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
      // Fallback: 기존 python-pptx 방식
      try {
        const blob = await api.createPptx(slides);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = generateFilename('발표자료', 'pptx', currentProject);
        a.click();
        URL.revokeObjectURL(url);
      } catch (err2: any) {
        setError(`PPTX 다운로드 실패: ${err2.message}`);
      }
    }
  }, [slides, currentProject]);

  // --- Slide Regenerate ---
  const handleRegenerate = useCallback(async () => {
    if (!editInstruction.trim() || slides.length === 0) return;
    setRegenerating(true);
    setError('');

    const current = slides[selectedIdx];
    const prev = selectedIdx > 0 ? slides[selectedIdx - 1] : undefined;
    const next = selectedIdx < slides.length - 1 ? slides[selectedIdx + 1] : undefined;

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
      <p className="text-sm text-[#787774] mb-6">프로젝트 문서 기반 PPT 생성 및 투자이력 업데이트</p>

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
          <button onClick={() => setError('')} className="ml-2 text-red-500 hover:text-red-800 font-bold">X</button>
        </div>
      )}

      {tab === 'generate' && (
        <div>
          {/* Project docs selector */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            <button onClick={() => setDocsOpen(!docsOpen)}
              className="flex items-center gap-2 text-sm font-medium text-[#37352F] w-full text-left">
              <span className={`transition-transform ${docsOpen ? 'rotate-90' : ''}`}>▶</span>
              참조 문서
              {currentProject && (
                <span className="text-xs text-[#787774] font-normal">
                  — {currentProject}
                  {totalDocs > 0 && ` (${selectedDocs.length > 0 ? `${selectedDocs.length}/${totalDocs}` : `전체 ${totalDocs}개`})`}
                </span>
              )}
            </button>
            {docsOpen && (
              <div className="mt-3">
                {!currentProject ? (
                  <div className="text-sm text-[#787774] py-4 text-center">
                    사이드바에서 프로젝트를 먼저 선택하세요
                  </div>
                ) : totalDocs === 0 ? (
                  <div className="text-sm text-[#787774] py-4 text-center">
                    프로젝트에 문서가 없습니다
                  </div>
                ) : (
                  <>
                    <div className="text-xs text-[#787774] mb-2">
                      특정 문서만 사용하려면 체크하세요. 미선택 시 전체 문서가 사용됩니다.
                    </div>
                    <div className="max-h-48 overflow-y-auto border border-[#E9E9E7] rounded-lg p-2">
                      <FolderTree
                        tree={tree}
                        projectName={currentProject}
                        selectable
                        selectedDocs={selectedDocs}
                        onSelectionChange={setSelectedDocs}
                        onDocDownload={(doc) => currentProject && api.downloadDoc(currentProject, doc)}
                      />
                    </div>
                    <div className="mt-3">
                      <div className="text-xs text-[#787774] mb-1.5">참조 문서 추가 업로드</div>
                      <FilePicker onFilesSelected={handleUploadFiles} loading={uploading} />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Context/instructions */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">발표 범위/지시사항</label>
            <textarea value={context} onChange={(e) => setContext(e.target.value)}
              placeholder="PPT에 포함할 범위, 강조할 내용, 특별 지시사항 (예: KPI 슬라이드 포함, 차트 강조 등)"
              rows={3}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none" />
          </div>

          {/* Generate / Outline / Stop */}
          {generating ? (
            <div className="flex gap-2 mb-4">
              <div className="flex-1 py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl text-center animate-pulse">
                슬라이드 생성 중... {slides.length > 0 ? `(${slides.length}장 완료)` : '(문서 분석 중)'}
              </div>
              <button onClick={() => { cancelRef.current = true; setGenerating(false); }}
                className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
                중지
              </button>
            </div>
          ) : outlineGenerating ? (
            <div className="flex gap-2 mb-4">
              <div className="flex-1 py-2.5 bg-[#37352F] text-white text-sm font-semibold rounded-xl text-center animate-pulse">
                아웃라인 생성 중...
              </div>
            </div>
          ) : (
            <div className="flex gap-2 mb-4">
              <button onClick={handleGenerateOutline} disabled={!currentProject || totalDocs === 0}
                className="flex-1 py-2.5 bg-[#37352F] text-white text-sm font-semibold rounded-xl hover:bg-[#2b2a28] disabled:bg-[#b0b0b0] transition-colors">
                아웃라인 먼저 생성
              </button>
              <button onClick={handleGenerate} disabled={!currentProject || totalDocs === 0}
                className="flex-1 py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors">
                바로 PPT 생성
              </button>
            </div>
          )}

          {/* Outline Editor */}
          {outline && !generating && (
            <div className="mb-4">
              <OutlineEditor
                outline={outline}
                onConfirm={handleConfirmOutline}
                onCancel={() => setOutline(null)}
              />
            </div>
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
              <button onClick={() => setUpdating(false)}
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
