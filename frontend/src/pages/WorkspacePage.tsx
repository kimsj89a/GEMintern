/**
 * WorkspacePage — NotebookLM 스타일 3열 작업 페이지
 * 왼쪽: 출처 (Sources) — 문서 목록 + 업로드
 * 가운데: 채팅 — RAG 기반 Q&A
 * 오른쪽: 스튜디오 — 도구 카드 그리드
 */
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import { unsubscribeTask } from '../api/ws';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';
import ChatWidget from '../components/ChatWidget';
import type { ChatMessage } from '../components/ChatWidget';
import SlideGeneratorModal from '../components/SlideGeneratorModal';

// 스튜디오 도구 → 기존 페이지 lazy import
const TOOL_PAGES: Record<string, React.LazyExoticComponent<any>> = {
  report: lazy(() => import('./WorkflowPage')),
  analysis: lazy(() => import('./WorkflowPage')),
  qa: lazy(() => import('./LpQaPage')),
  doc_update: lazy(() => import('./DocUpdaterPage')),
  draft: lazy(() => import('./DraftDocPage')),
  freedoc: lazy(() => import('./FreeDocPage')),
  ocr: lazy(() => import('./OcrPage')),
};

// ── 스튜디오 도구 정의 ──
const STUDIO_TOOLS = [
  { id: 'ppt', label: 'PPT 생성', icon: '📊', desc: '발표자료 슬라이드', page: 'ppt_tools' },
  { id: 'report', label: '보고서', icon: '📄', desc: '투심보고서, IM 등', page: 'phase2' },
  { id: 'analysis', label: '자료 분석', icon: '📥', desc: '사전 정보 수집', page: 'phase1' },
  { id: 'qa', label: 'LP Q&A', icon: '💬', desc: 'LP 질의 대응', page: 'lp_qa' },
  { id: 'doc_update', label: '문서 업데이트', icon: '🔄', desc: '기존 문서 수정', page: 'doc_updater' },
  { id: 'draft', label: '기안문', icon: '📝', desc: '기안문 작성', page: 'draftdoc' },
  { id: 'freedoc', label: '자유양식', icon: '✏️', desc: '자유 구조 문서', page: 'freedoc' },
  { id: 'ocr', label: 'OCR', icon: '👁', desc: '문서 텍스트 추출', page: 'ocr' },
];

export default function WorkspacePage() {
  const { currentProject, backToDashboard, activePanel, setActivePanel, openTab, setView } = useAppStore();
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [docCount, setDocCount] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [showSlideModal, setShowSlideModal] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  // streamingText 제거 — 향후 스트리밍 시 추가
  const cancelledRef = useRef(false);
  const activeTaskRef = useRef<string | null>(null);

  // Load docs
  const loadDocs = useCallback(() => {
    if (!currentProject) return;
    api.getProjectDocs(currentProject).then(data => {
      const folderTree = data.folder_tree || {};
      setTree(folderTree);
      setDocCount(data.count || 0);
      setSelectedDocs(Object.values(folderTree).flat() as string[]);
    }).catch(() => { setTree({}); setDocCount(0); });
  }, [currentProject]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  // Upload
  const handleUpload = useCallback(async (files: File[]) => {
    if (!currentProject) return;
    setUploading(true);
    try {
      await api.uploadFiles(currentProject, files);
      loadDocs();
    } catch {}
    setUploading(false);
  }, [currentProject, loadDocs]);

  // Chat send
  const handleSend = useCallback(async (text: string) => {
    if (!text.trim() || loading || !currentProject) return;
    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    // streaming reset
    cancelledRef.current = false;

    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'qa_answer',
        project_name: currentProject,
        kwargs: {
          question: text,
          selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
          project_name: currentProject,
        },
      });
      activeTaskRef.current = task_id;

      // Poll for result
      const poll = async () => {
        if (cancelledRef.current) return;
        try {
          const status = await api.getTaskStatus(task_id);
          if (status.status === 'complete') {
            const answer = typeof status.result === 'string' ? status.result : JSON.stringify(status.result);
            setMessages(prev => [...prev, { role: 'assistant', content: answer }]);
            // streaming reset
            setLoading(false);
          } else if (status.status === 'error') {
            setMessages(prev => [...prev, { role: 'assistant', content: `오류: ${status.error || '알 수 없는 오류'}` }]);
            setLoading(false);
          } else {
            setTimeout(poll, 1500);
          }
        } catch {
          setLoading(false);
        }
      };
      poll();
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `오류: ${err.message}` }]);
      setLoading(false);
    }
  }, [currentProject, selectedDocs, loading]);

  const handleStop = useCallback(() => {
    cancelledRef.current = true;
    if (activeTaskRef.current) {
      unsubscribeTask(activeTaskRef.current);
    }
    setLoading(false);
  }, []);

  const { activeTool, setActiveTool } = useAppStore();

  // Studio tool click — workspace 내에서 처리
  const handleToolClick = (toolId: string) => {
    if (toolId === 'ppt') {
      setShowSlideModal(true);
    } else {
      setActiveTool(toolId);
    }
  };

  const isMobile = window.innerWidth < 768;

  // ── 모바일: 패널 탭 전환 ──
  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-white">
        {/* 헤더 */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 shrink-0">
          <button onClick={backToDashboard} className="text-slate-400 hover:text-slate-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <span className="text-base font-bold text-slate-800 truncate">{currentProject}</span>
          <span className="text-xs text-slate-400 ml-auto">소스 {docCount}개</span>
        </div>

        {/* 콘텐츠 */}
        <div className="flex-1 overflow-hidden">
          {activePanel === 'sources' && (
            <div className="h-full overflow-y-auto p-4 space-y-3">
              <FilePicker onFilesSelected={handleUpload} loading={uploading} />
              <div className="text-xs text-slate-400">
                {selectedDocs.length > 0 ? `${selectedDocs.length}/${docCount}개 선택` : `전체 ${docCount}개`}
              </div>
              <FolderTree tree={tree} projectName={currentProject} selectable
                selectedDocs={selectedDocs} onSelectionChange={setSelectedDocs}
                onDocDownload={(doc) => api.downloadDoc(currentProject, doc)} />
            </div>
          )}
          {activePanel === 'chat' && (
            <div className="h-full flex flex-col">
              <ChatWidget messages={messages} onSend={handleSend} loading={loading}
                onStop={handleStop} placeholder="자료에 대해 질문하세요..." />
            </div>
          )}
          {activePanel === 'studio' && (
            <div className="h-full overflow-y-auto p-4">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">스튜디오</div>
              <div className="grid grid-cols-2 gap-3">
                {STUDIO_TOOLS.map(tool => (
                  <button key={tool.id} onClick={() => handleToolClick(tool.id)}
                    className="flex flex-col items-center gap-2 p-4 bg-slate-50 rounded-xl border border-slate-100 hover:border-slate-300 hover:shadow-sm transition-all">
                    <span className="text-2xl">{tool.icon}</span>
                    <span className="text-sm font-medium text-slate-700">{tool.label}</span>
                    <span className="text-[10px] text-slate-400">{tool.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 하단 탭 */}
        <div className="flex border-t border-slate-200 shrink-0 safe-area-bottom" style={{ height: 52 }}>
          {(['sources', 'chat', 'studio'] as const).map(panel => (
            <button key={panel} onClick={() => setActivePanel(panel)}
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 ${activePanel === panel ? 'text-blue-600' : 'text-slate-400'}`}>
              <span className="text-lg">{panel === 'sources' ? '📁' : panel === 'chat' ? '💬' : '🛠'}</span>
              <span className={`text-[10px] ${activePanel === panel ? 'font-semibold' : ''}`}>
                {panel === 'sources' ? '출처' : panel === 'chat' ? '채팅' : '스튜디오'}
              </span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ── 데스크톱: 3열 레이아웃 ──
  return (
    <div className="flex flex-col h-screen bg-white">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={backToDashboard} className="text-slate-400 hover:text-slate-600 transition-colors">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <span className="text-lg font-bold text-slate-800">{currentProject}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => { setView('legacy'); openTab('settings'); }}
            className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors">
            설정
          </button>
        </div>
      </div>

      {/* 3열 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 왼쪽: 출처 */}
        <div className="w-[300px] shrink-0 border-r border-slate-200 flex flex-col overflow-hidden">
          <div className="px-4 pt-4 pb-2 flex items-center justify-between">
            <span className="text-sm font-bold text-slate-700">출처</span>
            <span className="text-xs text-slate-400">{docCount}개</span>
          </div>
          <div className="px-4 pb-3">
            <FilePicker onFilesSelected={handleUpload} loading={uploading} />
          </div>
          <div className="flex-1 overflow-y-auto px-4 pb-4">
            <div className="text-xs text-slate-400 mb-2">
              {selectedDocs.length > 0 ? `${selectedDocs.length}/${docCount}개 선택` : '전체 선택됨'}
            </div>
            <FolderTree tree={tree} projectName={currentProject} selectable
              selectedDocs={selectedDocs} onSelectionChange={setSelectedDocs}
              onDocDownload={(doc) => api.downloadDoc(currentProject, doc)} />
          </div>
        </div>

        {/* 가운데: 채팅 또는 활성 도구 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {activeTool && TOOL_PAGES[activeTool] ? (
            <>
              <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
                <button onClick={() => setActiveTool(null)}
                  className="text-slate-400 hover:text-slate-600">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
                </button>
                <span className="text-sm font-bold text-slate-700">
                  {STUDIO_TOOLS.find(t => t.id === activeTool)?.label || activeTool}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto">
                <Suspense fallback={
                  <div className="flex items-center justify-center h-32">
                    <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                  </div>
                }>
                  {(() => { const ToolPage = TOOL_PAGES[activeTool]; return <ToolPage />; })()}
                </Suspense>
              </div>
            </>
          ) : (
            <>
              <div className="px-4 pt-4 pb-2">
                <span className="text-sm font-bold text-slate-700">채팅</span>
              </div>
              {messages.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                  <span className="text-5xl mb-4 opacity-50">💬</span>
                  <span className="text-sm">자료에 대해 질문하세요</span>
                  <span className="text-xs mt-1">소스 {docCount}개가 참조됩니다</span>
                </div>
              ) : null}
              <div className={messages.length > 0 ? 'flex-1 overflow-hidden' : 'hidden'}>
                <ChatWidget messages={messages} onSend={handleSend} loading={loading}
                  onStop={handleStop} placeholder="입력을 시작하세요..." />
              </div>
              {messages.length === 0 && (
                <div className="px-4 pb-4">
                  <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
                    <input
                      type="text"
                      placeholder="입력을 시작하세요..."
                      className="flex-1 bg-transparent text-sm outline-none text-slate-700 placeholder-slate-400"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.target as HTMLInputElement).value.trim()) {
                          handleSend((e.target as HTMLInputElement).value);
                          (e.target as HTMLInputElement).value = '';
                        }
                      }}
                    />
                    <span className="text-xs text-slate-400">소스 {docCount}개</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* 오른쪽: 스튜디오 */}
        <div className="w-[280px] shrink-0 border-l border-slate-200 overflow-y-auto">
          <div className="px-4 pt-4 pb-3">
            <span className="text-sm font-bold text-slate-700">스튜디오</span>
          </div>
          <div className="px-4 pb-4 space-y-2">
            {STUDIO_TOOLS.map(tool => (
              <button key={tool.id} onClick={() => handleToolClick(tool.id)}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-xl border border-slate-100 hover:border-slate-300 hover:bg-slate-50 transition-all text-left group">
                <span className="text-xl">{tool.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-700 group-hover:text-slate-900">{tool.label}</div>
                  <div className="text-[11px] text-slate-400">{tool.desc}</div>
                </div>
                <svg className="w-4 h-4 text-slate-300 group-hover:text-slate-500 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 18l6-6-6-6"/></svg>
              </button>
            ))}
          </div>

          <div className="px-4 pb-4 mt-4">
            <div className="text-center text-xs text-slate-400 mb-2">스튜디오 출력이 여기에 저장됩니다</div>
            <div className="text-center text-[11px] text-slate-300">소스를 추가한 후 도구를 선택하세요</div>
          </div>
        </div>
      </div>

      {/* 슬라이드 생성 모달 */}
      {showSlideModal && (
        <SlideGeneratorModal
          onClose={() => setShowSlideModal(false)}
          selectedDocs={selectedDocs.length > 0 ? selectedDocs : undefined}
        />
      )}
    </div>
  );
}
