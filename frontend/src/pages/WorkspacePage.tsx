/**
 * WorkspacePage — NotebookLM 스타일 3열 작업 페이지
 * 왼쪽: 출처 (Sources) — 문서 목록 + 업로드
 * 가운데: 채팅 — RAG 기반 Q&A
 * 오른쪽: 스튜디오 — 도구 카드 그리드
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import { unsubscribeTask } from '../api/ws';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';
import ChatWidget from '../components/ChatWidget';
import type { ChatMessage } from '../components/ChatWidget';
import SlideGeneratorModal from '../components/SlideGeneratorModal';
import WikiPanel from '../components/WikiPanel';
import ReviewWorkflowPanel from '../components/ReviewWorkflowPanel';
import ReportPanel from '../components/ReportPanel';
import QaPanel from '../components/QaPanel';
import ExcelModelPanel from '../components/ExcelModelPanel';
import DocAnalysisPanel from '../components/DocAnalysisPanel';
import ContractComparePanel from '../components/ContractComparePanel';
import { useLocalFolder } from '../hooks/useLocalFolder';

// ── 스튜디오 도구 정의 ──
const STUDIO_TOOLS = [
  { id: 'wiki', label: '위키', icon: '📖', desc: '프로젝트 위키' },
  { id: 'chat', label: '채팅', icon: '💬', desc: '자료 기반 Q&A' },
  { id: 'review', label: '검토', icon: '🔄', desc: '투자검토 워크플로' },
  { id: 'report', label: '보고서', icon: '📄', desc: '예비검토·투심보고서 등', page: 'phase2' },
  { id: 'qa', label: '질의회신', icon: '📋', desc: '배치 Q&A 대응', page: 'lp_qa' },
  { id: 'analysis', label: '자료 분석', icon: '🔍', desc: '문서별 순차 분석·요약' },
  { id: 'compare', label: '신구비교', icon: '⚖️', desc: '텀싯↔계약서 비교표' },
  { id: 'excel', label: 'Excel 모델', icon: '📊', desc: 'PEF 캐시플로우 모델' },
  { id: 'ppt', label: 'PPT 생성', icon: '📑', desc: '발표자료 슬라이드', page: 'ppt_tools' },
];


export default function WorkspacePage() {
  const { currentProject, backToDashboard, activePanel, setActivePanel, openTab, setView } = useAppStore();
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [docCount, setDocCount] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadFolder, setUploadFolder] = useState('__root__');
  const [showSlideModal, setShowSlideModal] = useState(false);
  const [leftWidth, setLeftWidth] = useState(300);

  // Local folder connection
  const localFolder = useLocalFolder();
  const [selectedLocalDocs, setSelectedLocalDocs] = useState<Set<string>>(new Set());

  const handleConnectFolder = useCallback(async () => {
    if (!currentProject) return;
    try {
      await localFolder.connect();
      // Index only — no upload. Files are read on-demand at analysis time.
    } catch (err: any) {
      if (err.message) alert(err.message);
    }
  }, [currentProject, localFolder]);

  const handleRescanFolder = useCallback(async () => {
    if (!currentProject) return;
    await localFolder.rescan();
  }, [currentProject, localFolder]);

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
      const allDocs = Object.values(folderTree).flat() as string[];
      setSelectedDocs(prev => {
        if (prev.length === 0) return allDocs; // first load → select all
        // Preserve selection: keep docs that still exist, default to all if none remain
        const remaining = prev.filter(d => allDocs.includes(d));
        return remaining.length > 0 ? remaining : allDocs;
      });
    }).catch((err) => { console.error('[loadDocs]', err); setTree({}); setDocCount(0); });
  }, [currentProject]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  // Read selected local files at analysis time.
  // Text files (.txt/.md/.csv/.json) → inline_docs dict passed in kwargs.
  // Binary files (.pdf/.docx/etc.) → upload on-demand, then RAG picks them up.
  const readLocalFilesForAnalysis = useCallback(async (): Promise<Record<string, string>> => {
    if (!localFolder.connected || selectedLocalDocs.size === 0) return {};
    const TEXT_EXTS = new Set(['.txt', '.md', '.csv', '.json']);
    const inline_docs: Record<string, string> = {};
    const binaryFiles: File[] = [];
    for (const lf of localFolder.files) {
      if (!selectedLocalDocs.has(lf.name)) continue;
      if (TEXT_EXTS.has(lf.ext)) {
        try { inline_docs[lf.name] = await lf.file.text(); } catch {}
      } else {
        binaryFiles.push(lf.file);
      }
    }
    if (binaryFiles.length > 0 && currentProject) {
      await api.uploadFiles(currentProject, binaryFiles);
      loadDocs();
    }
    return inline_docs;
  }, [localFolder, selectedLocalDocs, currentProject, loadDocs]);

  // Upload
  const handleUpload = useCallback(async (files: File[]) => {
    if (!currentProject) return;
    setUploading(true);
    try {
      await api.uploadFiles(currentProject, files, uploadFolder !== '__root__' ? uploadFolder : undefined);
      loadDocs();
    } catch {}
    setUploading(false);
  }, [currentProject, loadDocs, uploadFolder]);

  // Folder management
  const handleCreateFolder = useCallback(async (name: string) => {
    if (!currentProject) return;
    await api.createFolder(currentProject, name);
    loadDocs();
  }, [currentProject, loadDocs]);

  const handleRenameFolder = useCallback(async (folder: string, newLeaf: string) => {
    if (!currentProject) return;
    try { await api.renameFolder(currentProject, folder, newLeaf); loadDocs(); } catch {}
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
      const inlineDocs = await readLocalFilesForAnalysis();
      const { task_id } = await api.startAnalysis({
        task_type: 'qa_answer',
        project_name: currentProject,
        kwargs: {
          question: text,
          selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
          project_name: currentProject,
          ...(Object.keys(inlineDocs).length > 0 ? { inline_docs: inlineDocs } : {}),
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
    } else if (toolId === 'chat') {
      setActiveTool(null); // 기본 채팅 화면으로
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
              <FilePicker onFilesSelected={handleUpload} loading={uploading}
              localFolderConnected={localFolder.connected}
              localFolderName={localFolder.folderName}
              onConnectFolder={handleConnectFolder}
              onRescanFolder={handleRescanFolder}
              onDisconnectFolder={localFolder.disconnect}
              localScanning={localFolder.scanning}
            />
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
                onStop={handleStop} placeholder="자료에 대해 질문하세요..." projectName={currentProject} />
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
        {/* 왼쪽: 출처 (리사이즈 가능) */}
        <div style={{ width: leftWidth }} className="shrink-0 border-r border-slate-200 flex flex-col overflow-hidden">
          <div className="px-4 pt-4 pb-2 flex items-center justify-between">
            <span className="text-sm font-bold text-slate-700">출처</span>
            <span className="text-xs text-slate-400">{docCount}개</span>
          </div>
          <div className="px-4 pb-2 space-y-2">
            <FilePicker onFilesSelected={handleUpload} loading={uploading}
              localFolderConnected={localFolder.connected}
              localFolderName={localFolder.folderName}
              onConnectFolder={handleConnectFolder}
              onRescanFolder={handleRescanFolder}
              onDisconnectFolder={localFolder.disconnect}
              localScanning={localFolder.scanning}
            />
            {/* 업로드 대상 폴더 선택 */}
            {Object.keys(tree).filter(f => f !== '__root__').length > 0 && (
              <select
                value={uploadFolder}
                onChange={e => setUploadFolder(e.target.value)}
                className="w-full px-2 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-blue-400"
              >
                <option value="__root__">루트에 업로드</option>
                {Object.keys(tree).filter(f => f !== '__root__').sort().map(f => (
                  <option key={f} value={f}>{f}에 업로드</option>
                ))}
              </select>
            )}
          </div>
          <div className="flex-1 overflow-y-auto px-4 pb-4">
            <div className="text-xs text-slate-400 mb-2">
              {selectedDocs.length > 0 ? `${selectedDocs.length}/${docCount}개 선택` : '전체 선택됨'}
            </div>
            <FolderTree tree={tree} projectName={currentProject} selectable
              selectedDocs={selectedDocs} onSelectionChange={setSelectedDocs}
              onCreateFolder={handleCreateFolder}
              onFolderRename={handleRenameFolder}
              onDocDownload={(doc) => api.downloadDoc(currentProject, doc)}
              onDocDelete={async (doc) => {
                if (!confirm(`'${doc}' 파일을 삭제하시겠습니까?`)) return;
                try { await api.trashDoc(currentProject, doc); loadDocs(); } catch {}
              }}
              onFolderDelete={async (folder) => {
                if (!confirm(`'${folder}' 폴더를 삭제하시겠습니까?`)) return;
                try { await api.deleteFolder(currentProject, folder); loadDocs(); } catch {}
              }}
              onDocMove={async (doc, targetFolder) => {
                // Optimistic update
                setTree(prev => {
                  const next = { ...prev };
                  for (const f of Object.keys(next)) {
                    next[f] = next[f].filter(d => d !== doc);
                  }
                  if (!next[targetFolder]) next[targetFolder] = [];
                  next[targetFolder] = [...next[targetFolder], doc];
                  return next;
                });
                try { await api.moveDoc(currentProject, doc, targetFolder); } catch { loadDocs(); }
              }}
              onBatchMove={async (docs, targetFolder) => {
                // Optimistic update — move docs in local tree immediately
                setTree(prev => {
                  const next: Record<string, string[]> = {};
                  for (const f of Object.keys(prev)) {
                    next[f] = prev[f].filter(d => !docs.includes(d));
                  }
                  if (!next[targetFolder]) next[targetFolder] = [];
                  next[targetFolder] = [...next[targetFolder], ...docs];
                  return next;
                });
                // Fire API calls in background
                const promises = docs.map(doc =>
                  api.moveDoc(currentProject, doc, targetFolder).catch(() => {})
                );
                await Promise.all(promises);
                // Resync in case of errors
                loadDocs();
              }} />
            {/* 로컬 폴더 파일 목록 */}
            {localFolder.connected && localFolder.files.length > 0 && (
              <div className="mt-3 border-t border-slate-100 pt-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-emerald-700">💻 로컬 파일</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-slate-400">{localFolder.files.length}개</span>
                    <button
                      onClick={() => setSelectedLocalDocs(prev =>
                        prev.size === localFolder.files.length ? new Set() : new Set(localFolder.files.map(f => f.name))
                      )}
                      className="text-[10px] text-blue-500 hover:text-blue-700"
                    >
                      {selectedLocalDocs.size === localFolder.files.length ? '전체 해제' : '전체 선택'}
                    </button>
                  </div>
                </div>
                <div className="space-y-0.5 max-h-52 overflow-y-auto">
                  {localFolder.files.map(lf => (
                    <label key={lf.path} className="flex items-center gap-1.5 px-1 py-0.5 rounded hover:bg-slate-50 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={selectedLocalDocs.has(lf.name)}
                        onChange={e => setSelectedLocalDocs(prev => {
                          const next = new Set(prev);
                          e.target.checked ? next.add(lf.name) : next.delete(lf.name);
                          return next;
                        })}
                        className="w-3 h-3 accent-emerald-500 shrink-0"
                      />
                      <span className="text-[11px] text-slate-600 truncate flex-1" title={lf.path}>{lf.name}</span>
                      <span className="text-[10px] text-slate-300 shrink-0">{(lf.size / 1024).toFixed(0)}K</span>
                    </label>
                  ))}
                </div>
                {selectedLocalDocs.size > 0 && (
                  <button
                    onClick={async () => {
                      const toUpload = localFolder.files.filter(f => selectedLocalDocs.has(f.name)).map(f => f.file);
                      if (!toUpload.length || !currentProject) return;
                      setUploading(true);
                      try { await api.uploadFiles(currentProject, toUpload); loadDocs(); } catch {}
                      setUploading(false);
                    }}
                    disabled={uploading}
                    className="mt-1.5 w-full px-2 py-1 text-[11px] text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
                  >
                    ☁ 선택 파일 서버 업로드 ({selectedLocalDocs.size}개)
                  </button>
                )}
                <p className="mt-1.5 text-[10px] text-slate-400 leading-tight">
                  체크된 파일은 분석 시 자동 포함됩니다
                </p>
              </div>
            )}
          </div>
        </div>
        {/* 좌측 패널 리사이즈 핸들 */}
        <div
          onMouseDown={(e) => {
            e.preventDefault();
            const startX = e.clientX;
            const startW = leftWidth;
            const onMove = (ev: MouseEvent) => setLeftWidth(Math.min(500, Math.max(200, startW + ev.clientX - startX)));
            const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
            window.addEventListener('mousemove', onMove);
            window.addEventListener('mouseup', onUp);
          }}
          className="w-1 shrink-0 cursor-col-resize hover:bg-blue-200 transition-colors"
        />

        {/* 가운데: 채팅 또는 활성 도구 (wiki/review는 항상 마운트, display로 전환) */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* 위키 — 항상 마운트, display 토글 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${activeTool === 'wiki' ? '' : 'hidden'}`}>
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
              <button onClick={() => setActiveTool(null)}
                className="text-slate-400 hover:text-slate-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <span className="text-sm font-bold text-slate-700">📖 위키</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <WikiPanel projectName={currentProject} selectedDocs={selectedDocs} />
            </div>
          </div>

          {/* 검토 워크플로 — 항상 마운트, display 토글 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${activeTool === 'review' ? '' : 'hidden'}`}>
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
              <button onClick={() => setActiveTool(null)}
                className="text-slate-400 hover:text-slate-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <span className="text-sm font-bold text-slate-700">🔄 검토 워크플로</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <ReviewWorkflowPanel projectName={currentProject} />
            </div>
          </div>

          {/* 보고서 — 항상 마운트, display 토글 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${activeTool === 'report' ? '' : 'hidden'}`}>
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
              <button onClick={() => setActiveTool(null)}
                className="text-slate-400 hover:text-slate-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <span className="text-sm font-bold text-slate-700">📄 보고서</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <ReportPanel projectName={currentProject} selectedDocs={selectedDocs} />
            </div>
          </div>

          {/* 질의회신 — 항상 마운트, display 토글 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${activeTool === 'qa' ? '' : 'hidden'}`}>
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
              <button onClick={() => setActiveTool(null)}
                className="text-slate-400 hover:text-slate-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <span className="text-sm font-bold text-slate-700">📋 질의회신</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <QaPanel projectName={currentProject} selectedDocs={selectedDocs} />
            </div>
          </div>

          {/* Excel 모델 — 항상 마운트, display 토글 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${activeTool === 'excel' ? '' : 'hidden'}`}>
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
              <button onClick={() => setActiveTool(null)}
                className="text-slate-400 hover:text-slate-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <span className="text-sm font-bold text-slate-700">📊 Excel 모델</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <ExcelModelPanel projectName={currentProject} />
            </div>
          </div>

          {/* 자료 분석 — 항상 마운트, display 토글 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${activeTool === 'analysis' ? '' : 'hidden'}`}>
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
              <button onClick={() => setActiveTool(null)}
                className="text-slate-400 hover:text-slate-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <span className="text-sm font-bold text-slate-700">🔍 자료 분석</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <DocAnalysisPanel projectName={currentProject} selectedDocs={selectedDocs} />
            </div>
          </div>

          {/* 신구비교 — 항상 마운트, display 토글 */}
          <div className={`flex-1 flex flex-col overflow-hidden ${activeTool === 'compare' ? '' : 'hidden'}`}>
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
              <button onClick={() => setActiveTool(null)}
                className="text-slate-400 hover:text-slate-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <span className="text-sm font-bold text-slate-700">⚖️ 신구비교</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <ContractComparePanel projectName={currentProject} selectedDocs={selectedDocs} />
            </div>
          </div>

          {/* 기타 도구 — 조건부 렌더링 */}
          {activeTool && !['wiki', 'review', 'report', 'qa', 'excel', 'analysis', 'compare'].includes(activeTool) ? (
            <>
              <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-slate-100">
                <button onClick={() => setActiveTool(null)}
                  className="text-slate-400 hover:text-slate-600">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 18l-6-6 6-6"/></svg>
                </button>
                <span className="text-sm font-bold text-slate-700">
                  {STUDIO_TOOLS.find(t => t.id === activeTool)?.icon} {STUDIO_TOOLS.find(t => t.id === activeTool)?.label || activeTool}
                </span>
              </div>
              <div className="flex-1 flex flex-col overflow-hidden">
                {messages.length === 0 && (
                  <div className="px-6 py-4 bg-blue-50/50 border-b border-blue-100">
                    <div className="text-sm text-blue-700 font-medium mb-1">
                      {STUDIO_TOOLS.find(t => t.id === activeTool)?.icon} {STUDIO_TOOLS.find(t => t.id === activeTool)?.label}
                    </div>
                    <div className="text-xs text-blue-500">도구를 사용합니다.</div>
                  </div>
                )}
                <div className="flex-1 overflow-hidden">
                  <ChatWidget messages={messages} onSend={handleSend} loading={loading}
                    onStop={handleStop}
                    placeholder="요청 내용을 입력하세요..." projectName={currentProject} />
                </div>
              </div>
            </>
          ) : !activeTool ? (
            <>
              <div className="px-4 pt-4 pb-2 shrink-0">
                <span className="text-sm font-bold text-slate-700">채팅</span>
              </div>
              {messages.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                  <span className="text-5xl mb-4 opacity-50">💬</span>
                  <span className="text-sm">자료에 대해 질문하세요</span>
                  <span className="text-xs mt-1">소스 {selectedDocs.length || docCount}개가 참조됩니다</span>
                </div>
              ) : null}
              <div className={messages.length > 0 ? 'flex-1 overflow-hidden' : 'hidden'}>
                <ChatWidget messages={messages} onSend={handleSend} loading={loading}
                  onStop={handleStop} placeholder="입력을 시작하세요..." projectName={currentProject} />
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
                    <span className="text-xs text-slate-400">소스 {selectedDocs.length || docCount}개</span>
                  </div>
                </div>
              )}
            </>
          ) : null}
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
