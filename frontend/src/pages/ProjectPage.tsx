import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';

export default function ProjectPage() {
  const { currentProject, setCurrentProject } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [newProject, setNewProject] = useState('');
  const [newFolder, setNewFolder] = useState('');
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [vectorStats, setVectorStats] = useState<any>(null);
  const [syncData, setSyncData] = useState<any>(null);
  const [showSync, setShowSync] = useState(false);
  const [selectedSync, setSelectedSync] = useState<Set<string>>(new Set());
  const [syncing, setSyncing] = useState(false);
  const [status, setStatus] = useState('');
  const reindexAbortRef = useRef<AbortController | null>(null);

  const loadProjects = () => {
    api.listProjects().then(setProjects).catch(() => {});
  };

  const loadDocs = () => {
    if (!currentProject) { setTree({}); return; }
    api.getProjectDocs(currentProject).then((data) => {
      setTree(data.folder_tree || {});
    }).catch(() => {});
  };

  const loadVectorStats = () => {
    if (!currentProject) { setVectorStats(null); return; }
    api.vectorStats(currentProject).then(setVectorStats).catch(() => setVectorStats(null));
  };

  useEffect(() => { loadProjects(); }, []);
  const loadSyncStatus = () => {
    if (!currentProject) { setSyncData(null); return; }
    api.syncStatus(currentProject).then(setSyncData).catch(() => setSyncData(null));
  };

  useEffect(() => { loadDocs(); loadVectorStats(); }, [currentProject]);

  const handleCreateProject = async () => {
    if (!newProject.trim()) return;
    await api.createProject(newProject.trim());
    setNewProject('');
    loadProjects();
    setCurrentProject(newProject.trim());
  };

  const handleDeleteProject = async () => {
    if (!currentProject) return;
    if (!confirm(`'${currentProject}' 프로젝트를 삭제하시겠습니까?`)) return;
    await api.deleteProject(currentProject);
    setCurrentProject('');
    loadProjects();
  };

  const handleCreateFolder = async () => {
    if (!currentProject || !newFolder.trim()) return;
    await api.createFolder(currentProject, newFolder.trim());
    setNewFolder('');
    loadDocs();
  };

  const handleUpload = async (files: File[]) => {
    if (!currentProject) { setStatus('프로젝트를 먼저 선택하세요.'); return; }
    setUploading(true);
    setStatus('');
    try {
      const result = await api.uploadFiles(currentProject, files);
      const indexed = result?.indexed_count ?? result?.count ?? files.length;
      setStatus(`✅ ${files.length}개 파일 업로드 → DB 인덱싱 완료 (${indexed}건 등록됨)`);
      loadDocs();
    } catch {
      setStatus('❌ 업로드 실패');
    } finally {
      setUploading(false);
    }
  };

  const handleReindex = async (force = false) => {
    if (!currentProject) return;
    setReindexing(true);
    setStatus('');
    try {
      const result = await api.reindexProject(currentProject, force);
      if (result.success !== false) {
        const parts: string[] = [];
        if (result.added > 0) parts.push(`추가 ${result.added}`);
        if (result.modified > 0) parts.push(`변경 ${result.modified}`);
        if (result.deleted > 0) parts.push(`삭제 ${result.deleted}`);
        if (result.unchanged > 0) parts.push(`유지 ${result.unchanged}`);
        const detail = parts.length > 0 ? ` (${parts.join(', ')})` : '';
        setStatus(`✅ 벡터 인덱싱 완료: ${result.indexed_docs}개 처리 → 총 ${result.total_chunks}개 청크${detail}`);
      } else {
        setStatus(`❌ 인덱싱 실패: ${result.error}`);
      }
      loadVectorStats();
    } catch {
      setStatus('❌ 인덱싱 요청 실패');
    } finally {
      setReindexing(false);
    }
  };

  const handleDocDelete = async (doc: string) => {
    if (!currentProject) return;
    await api.trashDoc(currentProject, doc);
    loadDocs();
  };

  const handleFolderDelete = async (folder: string) => {
    if (!currentProject) return;
    await api.deleteFolder(currentProject, folder);
    loadDocs();
  };

  const handleDocMove = async (doc: string, targetFolder: string) => {
    if (!currentProject) return;
    await api.moveDoc(currentProject, doc, targetFolder);
    loadDocs();
  };

  const totalDocs = Object.values(tree).flat().length;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">📂 프로젝트 관리</h1>
      <p className="text-sm text-[#787774] mb-6">프로젝트별 문서를 관리합니다. 폴더로 정리하고, 파일을 업로드하세요.</p>

      {status && (
        <div className="mb-4 px-4 py-2 rounded-lg text-sm bg-blue-50 text-blue-700 border border-blue-200">
          {status}
          <button className="ml-2 text-blue-400" onClick={() => setStatus('')}>✕</button>
        </div>
      )}

      <div className="flex gap-6">
        {/* Left: project list + folder tree */}
        <div className="w-72 shrink-0">
          {/* New project */}
          <div className="flex gap-2 mb-4">
            <input
              value={newProject}
              onChange={(e) => setNewProject(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
              placeholder="새 프로젝트명"
              className="flex-1 px-3 py-1.5 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]"
            />
            <button onClick={handleCreateProject}
              className="px-3 py-1.5 bg-[#2383E2] text-white text-sm rounded-lg hover:bg-[#1b6ec2]">
              + 생성
            </button>
          </div>

          {/* Project selector */}
          <div className="mb-4">
            {projects.map((p) => {
              const name = p.name || p;
              return (
                <button
                  key={name}
                  onClick={() => setCurrentProject(name)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors ${
                    currentProject === name
                      ? 'bg-[#E8F3FC] text-[#2383E2] font-medium'
                      : 'hover:bg-[#F7F6F3] text-[#37352F]'
                  }`}
                >
                  📂 {name}
                </button>
              );
            })}
            {projects.length === 0 && (
              <div className="text-sm text-[#9B9A97] py-4 text-center">프로젝트가 없습니다.</div>
            )}
          </div>

          {currentProject && (
            <button onClick={handleDeleteProject}
              className="w-full text-left px-3 py-1.5 text-sm text-red-500 hover:bg-red-50 rounded-lg">
              🗑 프로젝트 삭제
            </button>
          )}
        </div>

        {/* Right: docs + upload */}
        <div className="flex-1">
          {currentProject ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-[#37352F]">
                  📂 {currentProject} <span className="text-[#9B9A97] font-normal">({totalDocs}건)</span>
                </h2>
                <div className="flex gap-2">
                  <input
                    value={newFolder}
                    onChange={(e) => setNewFolder(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
                    placeholder="폴더명"
                    className="px-2 py-1 border border-[#E9E9E7] rounded text-xs w-28 focus:outline-none focus:border-[#2383E2]"
                  />
                  <button onClick={handleCreateFolder}
                    className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">
                    + 폴더
                  </button>
                </div>
              </div>

              {/* Folder Tree */}
              <div className="bg-white border border-[#E9E9E7] rounded-xl p-3 mb-4 max-h-96 overflow-y-auto">
                {Object.keys(tree).length > 0 ? (
                  <FolderTree
                    tree={tree}
                    projectName={currentProject}
                    onDocDelete={handleDocDelete}
                    onFolderDelete={handleFolderDelete}
                    onDocMove={handleDocMove}
                  />
                ) : (
                  <div className="text-sm text-[#9B9A97] py-8 text-center">문서가 없습니다. 파일을 업로드하세요.</div>
                )}
              </div>

              {/* Vector Index Status */}
              <div className="flex items-center gap-3 mb-4 px-3 py-2 bg-[#F7F6F3] rounded-lg text-xs text-[#787774]">
                <span>
                  {vectorStats?.indexed
                    ? `벡터 DB: ${vectorStats.documents}개 문서, ${vectorStats.total_chunks}개 청크`
                    : '벡터 DB: 미인덱싱'}
                </span>
                {reindexing ? (
                  <button
                    onClick={() => { reindexAbortRef.current?.abort(); setReindexing(false); }}
                    className="ml-auto px-2 py-1 bg-[#EB5757] text-white border border-[#EB5757] rounded text-xs hover:bg-[#d94848]"
                  >
                    중지
                  </button>
                ) : (
                  <div className="ml-auto flex gap-1">
                    <button
                      onClick={() => handleReindex(false)}
                      className="px-2 py-1 bg-white border border-[#E9E9E7] rounded text-xs hover:bg-[#F7F6F3]"
                      title="변경된 문서만 인덱싱"
                    >
                      증분 인덱싱
                    </button>
                    <button
                      onClick={() => handleReindex(true)}
                      className="px-2 py-1 bg-white border border-[#E9E9E7] rounded text-xs hover:bg-[#F7F6F3] text-[#9B9A97]"
                      title="모든 문서 전체 재인덱싱"
                    >
                      전체
                    </button>
                  </div>
                )}
              </div>

              {/* RAG DB Sync Panel */}
              <div className="mb-4">
                <button
                  onClick={() => { setShowSync(!showSync); if (!showSync) { loadSyncStatus(); setSelectedSync(new Set()); } }}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-[#37352F] hover:bg-[#F7F6F3] rounded-lg w-full text-left"
                >
                  <span>{showSync ? '▾' : '▸'}</span>
                  <span className="font-medium">📊 RAG DB 동기화</span>
                  {syncData && (
                    <span className="ml-auto text-xs text-[#9B9A97]">
                      {syncData.total_disk}개 파일 / {syncData.total_indexed}개 인덱싱
                      {(syncData.disk_only > 0 || syncData.index_only > 0) && (
                        <span className="text-amber-500 ml-1">({syncData.disk_only + syncData.index_only}개 미동기화)</span>
                      )}
                    </span>
                  )}
                </button>

                {showSync && syncData && (() => {
                  const unsyncedDocs = syncData.docs.filter((d: any) => d.status !== 'synced');
                  const toggleDoc = (name: string) => {
                    setSelectedSync((prev) => {
                      const next = new Set(prev);
                      if (next.has(name)) next.delete(name); else next.add(name);
                      return next;
                    });
                  };
                  const selectAllUnsynced = () => {
                    setSelectedSync(new Set(unsyncedDocs.map((d: any) => d.name)));
                  };
                  const handleSyncSelected = async () => {
                    if (!currentProject || selectedSync.size === 0) return;
                    setSyncing(true);
                    const toAdd = syncData.docs
                      .filter((d: any) => d.status === 'disk_only' && selectedSync.has(d.name))
                      .map((d: any) => d.name);
                    const toRemove = syncData.docs
                      .filter((d: any) => d.status === 'index_only' && selectedSync.has(d.name))
                      .map((d: any) => d.name);
                    try {
                      const res = await api.syncDocs(currentProject, toAdd, toRemove);
                      if (res.success) {
                        setStatus(`✅ 동기화 완료: ${res.added}개 추가, ${res.removed}개 제거`);
                        loadSyncStatus();
                        loadDocs();
                        setSelectedSync(new Set());
                      } else {
                        setStatus(`❌ 동기화 실패: ${res.error}`);
                      }
                    } catch { setStatus('❌ 동기화 요청 실패'); }
                    setSyncing(false);
                  };

                  return (
                    <div className="bg-white border border-[#E9E9E7] rounded-xl p-3 mt-1">
                      {/* Summary */}
                      <div className="flex gap-3 mb-3 text-xs">
                        <span className="px-2 py-1 bg-green-50 text-green-700 rounded">✓ 동기화 {syncData.synced}</span>
                        {syncData.disk_only > 0 && <span className="px-2 py-1 bg-amber-50 text-amber-700 rounded">⚠ 미인덱싱 {syncData.disk_only}</span>}
                        {syncData.index_only > 0 && <span className="px-2 py-1 bg-red-50 text-red-700 rounded">✕ 고아 {syncData.index_only}</span>}
                      </div>

                      {/* Select all unsynced */}
                      {unsyncedDocs.length > 0 && (
                        <div className="flex items-center gap-2 mb-2 text-xs text-[#787774]">
                          <button onClick={selectAllUnsynced} className="hover:text-[#2383E2]">전체 선택</button>
                          <span>·</span>
                          <button onClick={() => setSelectedSync(new Set())} className="hover:text-[#2383E2]">선택 해제</button>
                        </div>
                      )}

                      {/* Doc list */}
                      <div className="max-h-56 overflow-y-auto space-y-0.5">
                        {syncData.docs.map((doc: any) => (
                          <label key={doc.name} className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs cursor-pointer hover:bg-[#F7F6F3] ${
                            doc.status === 'synced' ? 'text-[#787774]' :
                            doc.status === 'disk_only' ? 'text-amber-700' :
                            'text-red-700'
                          }`}>
                            {doc.status !== 'synced' ? (
                              <input
                                type="checkbox"
                                checked={selectedSync.has(doc.name)}
                                onChange={() => toggleDoc(doc.name)}
                                className="rounded border-gray-300"
                              />
                            ) : (
                              <span className="w-4 text-center text-green-500">✓</span>
                            )}
                            <span className={`w-5 text-center ${
                              doc.status === 'synced' ? 'text-green-500' :
                              doc.status === 'disk_only' ? 'text-amber-500' : 'text-red-500'
                            }`}>
                              {doc.status === 'synced' ? '' : doc.status === 'disk_only' ? '⚠' : '✕'}
                            </span>
                            <span className="flex-1 truncate">{doc.name}</span>
                            <span className="text-[#9B9A97]">{doc.size > 0 ? `${(doc.size / 1024).toFixed(0)}KB` : ''}</span>
                          </label>
                        ))}
                      </div>

                      {/* Sync action */}
                      {selectedSync.size > 0 && (
                        <button
                          onClick={handleSyncSelected}
                          disabled={syncing}
                          className="mt-3 w-full py-2 bg-[#2383E2] text-white text-xs font-medium rounded-lg hover:bg-[#1b6ec2] disabled:opacity-50"
                        >
                          {syncing ? '동기화 중...' : `🔄 선택한 ${selectedSync.size}개 파일 동기화`}
                        </button>
                      )}
                    </div>
                  );
                })()}
              </div>

              {/* File Upload */}
              <FilePicker onFilesSelected={handleUpload} loading={uploading} />
            </>
          ) : (
            <div className="flex items-center justify-center h-64 text-[#9B9A97] text-sm">
              ← 프로젝트를 선택하거나 새로 생성하세요.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
