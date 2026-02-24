import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import { subscribeTask, unsubscribeTask } from '../api/ws';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';
import ChatWidget from '../components/ChatWidget';
import type { ChatMessage } from '../components/ChatWidget';
import MarkdownViewer from '../components/MarkdownViewer';
import { copyRichText, extractTitle, downloadAsWord } from '../utils/clipboard';

const TEMPLATES = [
  { id: 'simple_review', label: '간단 검토' },
  { id: 'free_summary', label: '자유 요약' },
  { id: 'investment', label: '투자 보고서' },
  { id: 'management', label: '경영 분석' },
  { id: 'term_sheet', label: 'Term Sheet' },
  { id: 'loi_mou', label: 'LOI/MOU' },
  { id: 'im', label: 'IM 작성' },
];

// Phase config
const PHASE_CONFIG: Record<string, { title: string; desc: string; steps: { id: number; label: string }[] }> = {
  phase1: {
    title: '📥 사전 정보 수집',
    desc: '투자 대상 기업/자산의 기초 자료를 수집하고 분석합니다.',
    steps: [
      { id: 1, label: '자료 업로드' },
      { id: 2, label: '자료 분석' },
      { id: 3, label: '자료 Q&A' },
    ],
  },
  phase2: {
    title: '📝 투심보고서 작성',
    desc: '수집된 자료를 바탕으로 AI 투심보고서를 생성합니다.',
    steps: [
      { id: 1, label: '데이터 입력' },
      { id: 2, label: '보고서 생성' },
      { id: 3, label: '수정/보완' },
      { id: 4, label: '최종 결과' },
    ],
  },
  im: {
    title: '📑 문서작성',
    desc: 'AI 기반으로 문서를 자동 생성합니다.',
    steps: [
      { id: 1, label: '데이터 입력' },
      { id: 2, label: 'IM 생성' },
      { id: 3, label: '수정/보완' },
      { id: 4, label: '최종 결과' },
    ],
  },
};

export default function WorkflowPage() {
  const { currentProject, activePage } = useAppStore();
  const phase = PHASE_CONFIG[activePage] || PHASE_CONFIG.phase2;
  const isPhase1 = activePage === 'phase1';

  const [step, setStep] = useState(1);
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [context, setContext] = useState('');
  const [template, setTemplate] = useState(activePage === 'im' ? 'im' : 'simple_review');
  const [mode, setMode] = useState<'single' | 'chained'>('single');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');

  // Phase 1: analysis result
  const [analysisResult, setAnalysisResult] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  // Phase 1 & 3: Q&A / Refinement chat
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  // Cancel refs
  const cancelAnalyzeRef = useRef(false);
  const cancelGenerateRef = useRef(false);
  const cancelChatRef = useRef(false);
  const activeTaskRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!currentProject) return;
    api.getProjectDocs(currentProject).then((data) => {
      setTree(data.folder_tree || {});
    }).catch(() => {});
  }, [currentProject]);

  const handleUpload = async (files: File[]) => {
    if (!currentProject) return;
    setUploading(true);
    setUploadStatus('');
    try {
      const res = await api.uploadFiles(currentProject, files);
      const indexed = res?.indexed_count ?? res?.count ?? files.length;
      setUploadStatus(`✅ ${files.length}개 파일 → DB 인덱싱 완료 (${indexed}건)`);
      const data = await api.getProjectDocs(currentProject);
      setTree(data.folder_tree || {});
    } catch {
      setUploadStatus('❌ 업로드 실패');
    }
    setUploading(false);
  };

  // Phase 1: Analyze materials
  const handleAnalyze = async () => {
    if (!currentProject) return;
    setAnalyzing(true);
    setAnalysisResult('');
    setStep(2);
    cancelAnalyzeRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'material_summary',
        kwargs: {
          project_name: currentProject,
          selected_docs: selectedDocs,
        },
      });
      const check = async () => {
        if (cancelAnalyzeRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') { setAnalysisResult(status.result || ''); setAnalyzing(false); }
        else if (status.status === 'error') { setAnalysisResult(`오류: ${status.error}`); setAnalyzing(false); }
        else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) {
      setAnalysisResult(`오류: ${err.message}`);
      setAnalyzing(false);
    }
  };

  const handleStopAnalyze = () => {
    cancelAnalyzeRef.current = true;
    setAnalyzing(false);
  };

  // Phase 1: Q&A on materials
  const handlePhase1Chat = async (question: string) => {
    setChatMessages((prev) => [...prev, { role: 'user', content: question }]);
    setChatLoading(true);
    cancelChatRef.current = false;
    try {
      const { task_id } = await api.startQa({
        project_name: currentProject,
        question,
        selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
      });
      const check = async () => {
        if (cancelChatRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          setChatMessages((prev) => [...prev, { role: 'assistant', content: status.result || '' }]);
          setChatLoading(false);
        } else if (status.status === 'error') {
          setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${status.error}` }]);
          setChatLoading(false);
        } else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${err.message}` }]);
      setChatLoading(false);
    }
  };

  const handleStopChat = () => {
    cancelChatRef.current = true;
    setChatLoading(false);
  };

  // Phase 2: Generate report
  const handleGenerate = async () => {
    if (!currentProject) return;
    setGenerating(true);
    setStreamingText('');
    setResult('');
    setStep(2);
    cancelGenerateRef.current = false;

    try {
      const { task_id } = await api.startGenerate({
        project_name: currentProject,
        template_option: template,
        thinking_level: 'MEDIUM',
        file_context: context,
        inputs: { selected_docs: selectedDocs },
        mode,
      });
      activeTaskRef.current = task_id;

      subscribeTask(task_id, (msg) => {
        if (cancelGenerateRef.current) { unsubscribeTask(task_id); return; }
        if (msg.type === 'chunk' && msg.data) {
          setStreamingText((prev) => prev + msg.data);
        } else if (msg.type === 'complete') {
          setResult(msg.result || '');
          setStreamingText('');
          setGenerating(false);
          unsubscribeTask(task_id);
        } else if (msg.type === 'error') {
          setResult(`오류: ${msg.error}`);
          setStreamingText('');
          setGenerating(false);
          unsubscribeTask(task_id);
        }
      });

      // Fallback poll
      pollRef.current = setInterval(async () => {
        if (cancelGenerateRef.current) { if (pollRef.current) clearInterval(pollRef.current); return; }
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete' && !result) {
          if (pollRef.current) clearInterval(pollRef.current);
          setResult(status.result || '');
          setStreamingText('');
          setGenerating(false);
        } else if (status.status === 'error' && !result) {
          if (pollRef.current) clearInterval(pollRef.current);
          setResult(`오류: ${status.error}`);
          setStreamingText('');
          setGenerating(false);
        }
      }, 3000);
      setTimeout(() => { if (pollRef.current) clearInterval(pollRef.current); }, 600000);
    } catch (err: any) {
      setResult(`오류: ${err.message}`);
      setGenerating(false);
    }
  };

  const handleStopGenerate = () => {
    cancelGenerateRef.current = true;
    if (activeTaskRef.current) unsubscribeTask(activeTaskRef.current);
    if (pollRef.current) clearInterval(pollRef.current);
    // Keep whatever was streamed so far
    if (streamingText) setResult(streamingText);
    setStreamingText('');
    setGenerating(false);
  };

  // Phase 2 Step 3: Refine
  const handleRefine = async (feedback: string) => {
    setChatMessages((prev) => [...prev, { role: 'user', content: feedback }]);
    setChatLoading(true);
    cancelChatRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'refine',
        kwargs: { original_report: result, user_feedback: feedback, file_context: '' },
      });
      const check = async () => {
        if (cancelChatRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          setResult(status.result || '');
          setChatMessages((prev) => [...prev, { role: 'assistant', content: '보고서가 수정되었습니다.' }]);
          setChatLoading(false);
        } else if (status.status === 'error') {
          setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${status.error}` }]);
          setChatLoading(false);
        } else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${err.message}` }]);
      setChatLoading(false);
    }
  };

  const downloadMarkdown = () => {
    const text = result || analysisResult;
    const title = extractTitle(text) || `${currentProject}_${activePage}`;
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!currentProject) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <h1 className="text-xl font-bold text-[#37352F] mb-2">{phase.title}</h1>
        <div className="text-sm text-[#9B9A97] py-8 text-center">프로젝트를 먼저 선택하세요.</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">{phase.title}</h1>
      <p className="text-sm text-[#787774] mb-4">{phase.desc}</p>

      {/* Step indicator */}
      <div className="flex items-center gap-1 mb-6">
        {phase.steps.map((s, i) => (
          <div key={s.id} className="flex items-center">
            <button
              onClick={() => !generating && !analyzing && setStep(s.id)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                step === s.id
                  ? 'bg-[#2383E2] text-white'
                  : step > s.id
                    ? 'bg-[#E8F3FC] text-[#2383E2]'
                    : 'bg-[#F7F6F3] text-[#9B9A97]'
              }`}
            >
              {s.id}. {s.label}
            </button>
            {i < phase.steps.length - 1 && <span className="text-[#E9E9E7] mx-1">→</span>}
          </div>
        ))}
      </div>

      {/* ======================== PHASE 1 ======================== */}
      {isPhase1 && step === 1 && (
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="w-64 shrink-0 bg-white border border-[#E9E9E7] rounded-xl p-3 max-h-80 overflow-y-auto">
              <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">프로젝트 문서</div>
              <FolderTree tree={tree} projectName={currentProject} selectable selectedDocs={selectedDocs} onSelectionChange={setSelectedDocs} />
            </div>
            <div className="flex-1 space-y-4">
              <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
                <label className="block text-sm font-medium text-[#37352F] mb-2">추가 자료 업로드</label>
                <FilePicker onFilesSelected={handleUpload} loading={uploading} />
                {uploadStatus && (
                  <div className="mt-2 text-sm text-[#787774]">{uploadStatus}</div>
                )}
              </div>
              <button onClick={handleAnalyze}
                className="w-full py-3 bg-[#2383E2] text-white font-semibold rounded-xl hover:bg-[#1b6ec2] transition-colors text-sm">
                🔍 자료 분석 시작
              </button>
            </div>
          </div>
        </div>
      )}

      {isPhase1 && step === 2 && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-6">
          {analyzing && (
            <div className="flex items-center gap-3 mb-3">
              <span className="text-sm text-[#787774]">분석 중...</span>
              <button onClick={handleStopAnalyze}
                className="px-3 py-1 bg-[#EB5757] text-white text-xs rounded-lg hover:bg-[#d94848]">
                중지
              </button>
            </div>
          )}
          <div className="max-h-[60vh] overflow-y-auto">
            <MarkdownViewer content={analysisResult} />
          </div>
          {!analyzing && analysisResult && (
            <div className="flex gap-2 mt-4">
              <button onClick={() => setStep(3)} className="px-4 py-2 bg-[#2383E2] text-white text-sm rounded-lg hover:bg-[#1b6ec2]">
                자료 Q&A →
              </button>
              <button onClick={() => downloadAsWord(analysisResult)} className="px-4 py-2 border border-[#E9E9E7] text-sm rounded-lg hover:bg-[#F7F6F3]">
                📄 Word 저장
              </button>
              <button onClick={downloadMarkdown} className="px-4 py-2 border border-[#E9E9E7] text-sm rounded-lg hover:bg-[#F7F6F3]">
                📥 MD 저장
              </button>
            </div>
          )}
        </div>
      )}

      {isPhase1 && step === 3 && (
        <div className="flex gap-4" style={{ height: 'calc(100vh - 280px)' }}>
          <div className="flex-1 bg-white border border-[#E9E9E7] rounded-xl p-4 overflow-y-auto">
            <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">분석 결과</div>
            <MarkdownViewer content={analysisResult} />
          </div>
          <div className="w-96 bg-white border border-[#E9E9E7] rounded-xl p-4 flex flex-col">
            <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">자료 기반 Q&A</div>
            <ChatWidget messages={chatMessages} onSend={handlePhase1Chat} loading={chatLoading} onStop={handleStopChat} placeholder="자료에 대해 질문하세요..." />
          </div>
        </div>
      )}

      {/* ======================== PHASE 2 / IM ======================== */}
      {!isPhase1 && step === 1 && (
        <div className="space-y-4">
          <div className="flex gap-4">
            <div className="w-64 shrink-0 bg-white border border-[#E9E9E7] rounded-xl p-3 max-h-80 overflow-y-auto">
              <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">문서 선택</div>
              <FolderTree tree={tree} projectName={currentProject} selectable selectedDocs={selectedDocs} onSelectionChange={setSelectedDocs} />
            </div>
            <div className="flex-1 space-y-4">
              <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
                <label className="block text-sm font-medium text-[#37352F] mb-2">보고서 유형</label>
                <div className="flex flex-wrap gap-2">
                  {TEMPLATES.map((t) => (
                    <button key={t.id} onClick={() => setTemplate(t.id)}
                      className={`px-3 py-1.5 text-xs rounded-lg border ${template === t.id ? 'border-[#2383E2] bg-[#E8F3FC] text-[#2383E2]' : 'border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
                <label className="block text-sm font-medium text-[#37352F] mb-2">생성 모드</label>
                <div className="flex gap-3">
                  <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                    <input type="radio" checked={mode === 'single'} onChange={() => setMode('single')} /> 단일 생성
                  </label>
                  <label className="flex items-center gap-1.5 text-sm cursor-pointer">
                    <input type="radio" checked={mode === 'chained'} onChange={() => setMode('chained')} /> 체인 생성 (고품질)
                  </label>
                </div>
              </div>
              <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
                <label className="block text-sm font-medium text-[#37352F] mb-2">추가 컨텍스트</label>
                <textarea value={context} onChange={(e) => setContext(e.target.value)}
                  placeholder="보고서에 포함할 추가 정보나 지시사항..."
                  rows={4}
                  className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none" />
              </div>
              <FilePicker onFilesSelected={handleUpload} loading={uploading} />
              {uploadStatus && <div className="text-sm text-[#787774]">{uploadStatus}</div>}
              <button onClick={handleGenerate}
                className="w-full py-3 bg-[#2383E2] text-white font-semibold rounded-xl hover:bg-[#1b6ec2] transition-colors text-sm">
                🤖 보고서 생성 시작
              </button>
            </div>
          </div>
        </div>
      )}

      {!isPhase1 && step === 2 && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-6">
          {generating && (
            <div className="flex items-center gap-3 mb-3">
              <div className="flex-1">
                <div className="text-sm text-[#787774] mb-1">생성 중...</div>
                <div className="w-full bg-[#E9E9E7] rounded-full h-1.5">
                  <div className="bg-[#2383E2] h-1.5 rounded-full animate-pulse" style={{ width: '60%' }} />
                </div>
              </div>
              <button onClick={handleStopGenerate}
                className="px-4 py-2 bg-[#EB5757] text-white text-sm font-semibold rounded-lg hover:bg-[#d94848]">
                중지
              </button>
            </div>
          )}
          <div className="max-h-[60vh] overflow-y-auto">
            <MarkdownViewer content={streamingText || result} />
          </div>
          {!generating && result && (
            <div className="flex gap-2 mt-4">
              <button onClick={() => setStep(3)} className="px-4 py-2 bg-[#2383E2] text-white text-sm rounded-lg hover:bg-[#1b6ec2]">수정/보완 →</button>
              <button onClick={() => setStep(4)} className="px-4 py-2 border border-[#E9E9E7] text-sm rounded-lg hover:bg-[#F7F6F3]">최종 결과로 →</button>
            </div>
          )}
        </div>
      )}

      {!isPhase1 && step === 3 && (
        <div className="flex gap-4" style={{ height: 'calc(100vh - 280px)' }}>
          <div className="flex-1 bg-white border border-[#E9E9E7] rounded-xl p-4 overflow-y-auto">
            <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">현재 보고서</div>
            <MarkdownViewer content={result} />
          </div>
          <div className="w-96 bg-white border border-[#E9E9E7] rounded-xl p-4 flex flex-col">
            <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">수정 요청</div>
            <ChatWidget messages={chatMessages} onSend={handleRefine} loading={chatLoading} onStop={handleStopChat} placeholder="수정할 내용을 입력하세요..." />
          </div>
        </div>
      )}

      {!isPhase1 && step === 4 && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold text-[#37352F]">📄 최종 결과</div>
            <div className="flex gap-2">
              <button onClick={() => downloadAsWord(result)} className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3]">📄 Word 저장</button>
              <button onClick={downloadMarkdown} className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3]">📥 MD 저장</button>
              <button onClick={() => copyRichText(result)} className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3]">복사</button>
            </div>
          </div>
          <div className="max-h-[60vh] overflow-y-auto">
            <MarkdownViewer content={result} />
          </div>
        </div>
      )}
    </div>
  );
}
