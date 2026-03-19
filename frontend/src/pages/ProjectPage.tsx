import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';
import FolderScanModal from '../components/FolderScanModal';
import { listLocalProjects, getProjectDocuments } from '../utils/projectDB';
import { ensureServerSync, resetSyncCache } from '../utils/autoSync';

function IdbMigrationBanner({ onDone }: { onDone: () => void }) {
  const [idbProjects, setIdbProjects] = useState<any[]>([]);
  const [migrating, setMigrating] = useState(false);
  const [status, setStatus] = useState('');
  const [dismissed, setDismissed] = useState(() => localStorage.getItem('idb_migration_done') === '1');

  useEffect(() => {
    if (dismissed) return;
    listLocalProjects().then(async (locals) => {
      if (locals.length === 0) { setDismissed(true); localStorage.setItem('idb_migration_done', '1'); return; }
      // Check which ones are NOT on server yet
      try {
        const serverList = await api.listProjects();
        const serverNames = new Set(serverList.map((p: any) => p.name));
        const missing = locals.filter(p => !serverNames.has(p.name));
        setIdbProjects(missing);
        if (missing.length === 0) { setDismissed(true); localStorage.setItem('idb_migration_done', '1'); }
      } catch { setIdbProjects(locals); }
    }).catch(() => {});
  }, [dismissed]);

  if (dismissed || idbProjects.length === 0) return null;

  const handleMigrate = async () => {
    setMigrating(true);
    let migrated = 0;
    for (const proj of idbProjects) {
      setStatus(`${proj.name} 마이그레이션 중...`);
      try {
        // Create project on server
        try { await api.createProject(proj.name); } catch {}
        // Get documents from IDB and sync
        const docs = await getProjectDocuments(proj.name);
        const validDocs = docs.filter(d => d.filename !== '__folder_placeholder__' && d.parsedText);
        if (validDocs.length > 0) {
          await api.syncTextsToServer(proj.name, validDocs.map(d => ({
            filename: d.filename, parsedText: d.parsedText, folder: d.folder,
          })));
        }
        migrated++;
      } catch (err) {
        console.error(`Migration failed for ${proj.name}:`, err);
      }
    }
    setStatus(`${migrated}개 프로젝트 마이그레이션 완료!`);
    setMigrating(false);
    localStorage.setItem('idb_migration_done', '1');
    setTimeout(() => { setDismissed(true); onDone(); }, 2000);
  };

  return (
    <div className="mb-4 px-4 py-3 rounded-xl bg-amber-50 border border-amber-200">
      <div className="text-sm font-medium text-amber-800 mb-1">
        브라우저에 {idbProjects.length}개 프로젝트가 남아있습니다
      </div>
      <div className="text-xs text-amber-700 mb-2">
        {idbProjects.map(p => p.name).join(', ')} — 서버로 이전하면 어디서든 접근 가능합니다.
      </div>
      {status && <div className="text-xs text-amber-600 mb-2">{status}</div>}
      <div className="flex gap-2">
        <button onClick={handleMigrate} disabled={migrating}
          className="px-3 py-1.5 text-xs bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:bg-amber-300">
          {migrating ? '마이그레이션 중...' : '서버로 이전'}
        </button>
        <button onClick={() => { setDismissed(true); localStorage.setItem('idb_migration_done', '1'); }}
          className="px-3 py-1.5 text-xs text-amber-600 hover:bg-amber-100 rounded-lg">
          무시
        </button>
      </div>
    </div>
  );
}

export default function ProjectPage() {
  const { currentProject, setCurrentProject } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [newProject, setNewProject] = useState('');
  const [newFolder, setNewFolder] = useState('');
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');
  const [docCount, setDocCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [showFolderScan, setShowFolderScan] = useState(false);

  const loadProjects = async () => {
    try {
      const list = await api.listProjects();
      setProjects(list);
    } catch { setProjects([]); }
  };

  const loadDocs = async () => {
    if (!currentProject) { setTree({}); setDocCount(0); return; }
    try {
      const data = await api.getProjectDocs(currentProject);
      setTree(data.folder_tree || {});
      setDocCount(data.count || 0);
    } catch { setTree({}); setDocCount(0); }
  };

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { loadDocs(); }, [currentProject]);

  const handleCreateProject = async () => {
    if (!newProject.trim()) return;
    try {
      await api.createProject(newProject.trim());
      setCurrentProject(newProject.trim());
      setNewProject('');
      loadProjects();
    } catch { setStatus('프로젝트 생성 실패'); }
  };

  const handleRenameProject = async () => {
    if (!currentProject) return;
    const newName = prompt('새 프로젝트명을 입력하세요:', currentProject);
    if (!newName || newName.trim() === currentProject) return;
    try {
      const result = await api.renameProject(currentProject, newName.trim());
      if (result.success) {
        setCurrentProject(result.name);
        loadProjects();
        setStatus('프로젝트 이름 변경 완료');
      }
    } catch { setStatus('프로젝트 이름 변경 실패'); }
  };

  const handleDeleteProject = async () => {
    if (!currentProject) return;
    if (!confirm(`'${currentProject}' 프로젝트를 삭제하시겠습니까?`)) return;
    try {
      await api.deleteProject(currentProject);
      setCurrentProject('');
      loadProjects();
    } catch { setStatus('프로젝트 삭제 실패'); }
  };

  const handleCreateFolder = async () => {
    if (!currentProject || !newFolder.trim()) return;
    try {
      await api.createFolder(currentProject, newFolder.trim());
      setNewFolder('');
      loadDocs();
    } catch { setStatus('폴더 생성 실패'); }
  };

  const handleUpload = async (files: File[]) => {
    if (!currentProject) { setStatus('프로젝트를 먼저 선택하세요.'); return; }
    setUploading(true);
    setStatus('');
    try {
      const result = await api.uploadFiles(currentProject, files);
      const count = Object.keys(result.parsed_texts || {}).length;
      const errorMsg = result.parse_errors?.length > 0 ? ` (${result.parse_errors.length}개 파일 파싱 실패)` : '';
      setStatus(`${count}개 파일 업로드 완료${errorMsg}`);
      loadDocs();
    } catch { setStatus('업로드 실패'); } finally { setUploading(false); }
  };

  const handleForceSync = async () => {
    if (!currentProject) return;
    setSyncing(true);
    setStatus('IndexedDB에서 서버로 동기화 중...');
    try {
      resetSyncCache(currentProject);
      await ensureServerSync(currentProject, true);
      await loadDocs();
      await loadProjects();
      const localDocs = await getProjectDocuments(currentProject);
      const realDocs = localDocs.filter(d => d.filename !== '__folder_placeholder__' && d.parsedText);
      setStatus(`동기화 완료! (IndexedDB: ${realDocs.length}개 → 서버)`);
    } catch {
      setStatus('동기화 실패');
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncAll = async () => {
    setSyncing(true);
    setStatus('모든 프로젝트 동기화 중...');
    try {
      const localProjects = await listLocalProjects();
      let total = 0;
      for (const proj of localProjects) {
        resetSyncCache(proj.name);
        const localDocs = await getProjectDocuments(proj.name);
        const realDocs = localDocs.filter(d => d.filename !== '__folder_placeholder__' && d.parsedText);
        if (realDocs.length === 0) continue;
        // Ensure project exists on server
        try { await api.createProject(proj.name); } catch {}
        await ensureServerSync(proj.name, true);
        total += realDocs.length;
      }
      await loadProjects();
      if (currentProject) await loadDocs();
      setStatus(`전체 동기화 완료! (${localProjects.length}개 프로젝트, ${total}개 문서)`);
    } catch {
      setStatus('전체 동기화 실패');
    } finally {
      setSyncing(false);
    }
  };

  const handleDocDelete = async (doc: string) => {
    if (!currentProject) return;
    if (!confirm(`'${doc}' 문서를 삭제하시겠습니까?`)) return;
    try {
      const result = await api.trashDoc(currentProject, doc);
      if (result?.success === false) {
        setStatus(result.error || '문서 삭제 실패');
      } else {
        loadDocs();
      }
    } catch (err: any) { setStatus(`문서 삭제 실패: ${err.message}`); }
  };

  const handleFolderDelete = async (folder: string) => {
    if (!currentProject) return;
    try {
      await api.deleteFolder(currentProject, folder);
      loadDocs();
    } catch { setStatus('폴더 삭제 실패'); }
  };

  const handleDocMove = async (doc: string, targetFolder: string) => {
    if (!currentProject) return;
    try {
      await api.moveDoc(currentProject, doc, targetFolder);
      loadDocs();
    } catch { setStatus('문서 이동 실패'); }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-lg font-semibold text-[#37352F] tracking-tight mb-0.5">프로젝트 관리</h1>
      <p className="text-[13px] text-[#787774] mb-6">프로젝트별 문서를 관리합니다</p>
      <IdbMigrationBanner onDone={loadProjects} />
      {status && (
        <div className="mb-4 px-4 py-2.5 rounded-lg text-[13px] bg-blue-50/80 text-blue-700 border border-blue-100 flex items-center justify-between">
          <span>{status}</span>
          <button className="text-blue-400 hover:text-blue-600 text-xs font-medium ml-3" onClick={() => setStatus('')}>닫기</button>
        </div>
      )}
      <div className="flex gap-6">
        {/* Sidebar — Project List */}
        <div className="w-64 shrink-0">
          <div className="flex gap-1.5 mb-3">
            <input value={newProject} onChange={(e) => setNewProject(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
              placeholder="새 프로젝트명"
              className="flex-1 px-3 py-1.5 border border-[#E9E9E7] rounded-lg text-[13px] focus:outline-none focus:border-[#2383E2] focus:ring-1 focus:ring-[#2383E2]/20 transition-shadow" />
            <button onClick={handleCreateProject}
              className="px-3 py-1.5 bg-[#2383E2] text-white text-[13px] font-medium rounded-lg hover:bg-[#1b6ec2] transition-colors whitespace-nowrap">생성</button>
          </div>
          <div className="mb-3 space-y-0.5">
            {projects.map((p) => {
              const name = p.name || p;
              const isActive = currentProject === name;
              return (
                <button key={name} onClick={() => setCurrentProject(name)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-[13px] transition-all flex items-center justify-between group ${isActive
                    ? 'bg-[#2383E2]/10 text-[#2383E2] font-medium shadow-sm shadow-[#2383E2]/5'
                    : 'hover:bg-[#F7F6F3] text-[#37352F]'}`}>
                  <span className="truncate">{name}</span>
                  {p.doc_count != null && (
                    <span className={`text-[11px] tabular-nums px-1.5 py-0.5 rounded-full ${isActive ? 'bg-[#2383E2]/15 text-[#2383E2]' : 'bg-[#F0F0EE] text-[#9B9A97]'}`}>
                      {p.doc_count}
                    </span>
                  )}
                </button>
              );
            })}
            {projects.length === 0 && (
              <div className="text-[13px] text-[#9B9A97] py-6 text-center">프로젝트를 생성하세요</div>
            )}
          </div>
          {currentProject && (
            <div className="flex gap-1 border-t border-[#E9E9E7] pt-2">
              <button onClick={handleRenameProject}
                className="flex-1 px-2 py-1.5 text-[12px] text-[#787774] hover:bg-[#F7F6F3] hover:text-[#37352F] rounded-lg transition-colors">이름 변경</button>
              <button onClick={handleDeleteProject}
                className="flex-1 px-2 py-1.5 text-[12px] text-[#787774] hover:bg-red-50 hover:text-red-500 rounded-lg transition-colors">삭제</button>
            </div>
          )}
          <button onClick={handleSyncAll} disabled={syncing}
            className="w-full mt-3 px-3 py-1.5 text-[11px] text-[#787774] hover:text-blue-600 hover:bg-blue-50/50 rounded-lg border border-[#E9E9E7] disabled:opacity-40 transition-colors">
            {syncing ? '동기화 중...' : '전체 IndexedDB → 서버 동기화'}
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {currentProject ? (
            <>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-[14px] font-semibold text-[#37352F] tracking-tight flex items-center gap-2">
                  {currentProject}
                  <span className="text-[12px] font-normal text-[#9B9A97] tabular-nums">{docCount}개 문서</span>
                </h2>
              </div>
              <div className="flex items-center gap-1.5 mb-3">
                <input value={newFolder} onChange={(e) => setNewFolder(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
                  placeholder="폴더명"
                  className="px-2.5 py-1 border border-[#E9E9E7] rounded-lg text-[12px] w-24 focus:outline-none focus:border-[#2383E2] focus:ring-1 focus:ring-[#2383E2]/20 transition-shadow" />
                <button onClick={handleCreateFolder}
                  className="px-2.5 py-1 text-[12px] text-[#787774] border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] hover:text-[#37352F] transition-colors whitespace-nowrap">+ 폴더</button>
                <button onClick={() => setShowFolderScan(true)}
                  className="px-2.5 py-1 text-[12px] text-violet-600 border border-violet-200 rounded-lg bg-violet-50 hover:bg-violet-100 transition-colors whitespace-nowrap">📁 폴더 스캔</button>
              </div>

              {/* File Tree */}
              <div className="bg-white border border-[#E9E9E7] rounded-xl p-3 mb-4 max-h-[420px] overflow-y-auto shadow-sm shadow-black/[0.03]">
                {Object.keys(tree).length > 0 ? (
                  <FolderTree tree={tree} projectName={currentProject}
                    onDocDelete={handleDocDelete}
                    onDocDownload={(doc) => currentProject && api.downloadDoc(currentProject, doc)}
                    onFolderDelete={handleFolderDelete}
                    onDocMove={handleDocMove} />
                ) : (
                  <div className="text-[13px] text-[#9B9A97] py-10 text-center">
                    <div className="text-2xl mb-2 opacity-40">📂</div>
                    문서가 없습니다. 아래에서 파일을 업로드하세요.
                  </div>
                )}
              </div>

              {/* Sync bar */}
              <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-[#FAFAF9] rounded-lg text-[12px] text-[#787774] border border-[#F0F0EE]">
                <span className="tabular-nums">서버 저장: {docCount}개</span>
                <span className="text-[#E0E0DE]">|</span>
                <button onClick={handleForceSync} disabled={syncing}
                  className="text-[12px] text-blue-600 hover:text-blue-700 font-medium disabled:opacity-40 transition-colors">
                  {syncing ? '동기화 중...' : 'IndexedDB 동기화'}
                </button>
              </div>

              {/* Upload */}
              <FilePicker onFilesSelected={handleUpload} loading={uploading} />

              {/* Folder Scan Modal */}
              {showFolderScan && (
                <FolderScanModal
                  projectName={currentProject}
                  onClose={() => setShowFolderScan(false)}
                  onComplete={() => loadDocs()}
                />
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-72 text-[#9B9A97]">
              <div className="text-3xl mb-3 opacity-30">📋</div>
              <div className="text-[13px]">프로젝트를 선택하거나 새로 생성하세요</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
