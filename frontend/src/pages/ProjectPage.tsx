import { useEffect, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';
import {
  listLocalProjects, createLocalProject, deleteLocalProject,
  addLocalDocuments, getLocalFolderTree, deleteLocalDocument,
  deleteLocalFolder, moveLocalDocument, createLocalFolder,
  getProjectDocuments,
} from '../utils/projectDB';

export default function ProjectPage() {
  const { currentProject, setCurrentProject } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [newProject, setNewProject] = useState('');
  const [newFolder, setNewFolder] = useState('');
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');
  const [docCount, setDocCount] = useState(0);

  const loadProjects = async () => {
    try {
      const list = await listLocalProjects();
      setProjects(list.sort((a, b) => b.createdAt - a.createdAt));
    } catch { setProjects([]); }
  };

  const loadDocs = async () => {
    if (!currentProject) { setTree({}); return; }
    try { const t = await getLocalFolderTree(currentProject); setTree(t); }
    catch { setTree({}); }
  };

  useEffect(() => { loadProjects(); }, []);
  useEffect(() => { loadDocs(); }, [currentProject]);

  useEffect(() => {
    if (!currentProject) { setDocCount(0); return; }
    getProjectDocuments(currentProject).then(docs => {
      setDocCount(docs.filter(d => d.filename !== '__folder_placeholder__').length);
    });
  }, [currentProject, tree]);

  const handleCreateProject = async () => {
    if (!newProject.trim()) return;
    await createLocalProject(newProject.trim());
    setNewProject('');
    loadProjects();
    setCurrentProject(newProject.trim());
  };

  const handleDeleteProject = async () => {
    if (!currentProject) return;
    if (!confirm(`'${currentProject}' 프로젝트를 삭제하시겠습니까?`)) return;
    await deleteLocalProject(currentProject);
    setCurrentProject('');
    loadProjects();
  };

  const handleCreateFolder = async () => {
    if (!currentProject || !newFolder.trim()) return;
    await createLocalFolder(currentProject, newFolder.trim());
    setNewFolder('');
    loadDocs();
  };

  const handleUpload = async (files: File[]) => {
    if (!currentProject) { setStatus('프로젝트를 먼저 선택하세요.'); return; }
    setUploading(true);
    setStatus('');
    try {
      const result = await api.parseFiles(files);
      const docs = Object.entries(result.parsed_texts).map(([filename, text]) => ({ filename, parsedText: text as string }));
      await addLocalDocuments(currentProject, docs);
      const errorMsg = result.errors.length > 0 ? ` (${result.errors.length}개 파일 파싱 실패)` : '';
      setStatus(`${docs.length}개 파일 업로드 완료${errorMsg}. 서버 동기화 중...`);
      loadDocs();
      // 백그라운드로 서버 RAG 저장소에 동기화
      api.syncTextsToServer(currentProject, docs).then(() => {
        setStatus(`${docs.length}개 파일 업로드 완료${errorMsg}. 서버 동기화 완료.`);
      }).catch(() => {
        setStatus(`${docs.length}개 파일 업로드 완료${errorMsg}. 서버 동기화 실패 (로컬은 정상).`);
      });
    } catch { setStatus('업로드 실패'); } finally { setUploading(false); }
  };

  const handleDocDelete = async (doc: string) => {
    if (!currentProject) return;
    for (const [folder, docs] of Object.entries(tree)) {
      if (docs.includes(doc)) { await deleteLocalDocument(currentProject, folder, doc); break; }
    }
    loadDocs();
  };

  const handleFolderDelete = async (folder: string) => {
    if (!currentProject) return;
    await deleteLocalFolder(currentProject, folder);
    loadDocs();
  };

  const handleDocMove = async (doc: string, targetFolder: string) => {
    if (!currentProject) return;
    for (const [folder, docs] of Object.entries(tree)) {
      if (docs.includes(doc)) { await moveLocalDocument(currentProject, doc, folder, targetFolder); break; }
    }
    loadDocs();
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">프로젝트 관리</h1>
      <p className="text-sm text-[#787774] mb-6">프로젝트별 문서를 관리합니다. 파일은 브라우저에 로컬 저장됩니다.</p>
      {status && (
        <div className="mb-4 px-4 py-2 rounded-lg text-sm bg-blue-50 text-blue-700 border border-blue-200">
          {status}
          <button className="ml-2 text-blue-400" onClick={() => setStatus('')}>x</button>
        </div>
      )}
      <div className="flex gap-6">
        <div className="w-72 shrink-0">
          <div className="flex gap-2 mb-4">
            <input value={newProject} onChange={(e) => setNewProject(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
              placeholder="새 프로젝트명"
              className="flex-1 px-3 py-1.5 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]" />
            <button onClick={handleCreateProject}
              className="px-3 py-1.5 bg-[#2383E2] text-white text-sm rounded-lg hover:bg-[#1b6ec2]">+ 생성</button>
          </div>
          <div className="mb-4">
            {projects.map((p) => {
              const name = p.name || p;
              return (
                <button key={name} onClick={() => setCurrentProject(name)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors ${currentProject === name ? 'bg-[#E8F3FC] text-[#2383E2] font-medium' : 'hover:bg-[#F7F6F3] text-[#37352F]'}`}>
                  {name}
                </button>
              );
            })}
            {projects.length === 0 && (
              <div className="text-sm text-[#9B9A97] py-4 text-center">프로젝트가 없습니다.</div>
            )}
          </div>
          {currentProject && (
            <button onClick={handleDeleteProject}
              className="w-full text-left px-3 py-1.5 text-sm text-red-500 hover:bg-red-50 rounded-lg">프로젝트 삭제</button>
          )}
        </div>
        <div className="flex-1">
          {currentProject ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-[#37352F]">
                  {currentProject} <span className="text-[#9B9A97] font-normal">({docCount}건)</span>
                </h2>
                <div className="flex gap-2">
                  <input value={newFolder} onChange={(e) => setNewFolder(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
                    placeholder="폴더명"
                    className="px-2 py-1 border border-[#E9E9E7] rounded text-xs w-28 focus:outline-none focus:border-[#2383E2]" />
                  <button onClick={handleCreateFolder}
                    className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">+ 폴더</button>
                </div>
              </div>
              <div className="bg-white border border-[#E9E9E7] rounded-xl p-3 mb-4 max-h-96 overflow-y-auto">
                {Object.keys(tree).length > 0 ? (
                  <FolderTree tree={tree} projectName={currentProject}
                    onDocDelete={handleDocDelete} onFolderDelete={handleFolderDelete} onDocMove={handleDocMove} />
                ) : (
                  <div className="text-sm text-[#9B9A97] py-8 text-center">문서가 없습니다. 파일을 업로드하세요.</div>
                )}
              </div>
              <div className="flex items-center gap-3 mb-4 px-3 py-2 bg-[#F7F6F3] rounded-lg text-xs text-[#787774]">
                <span>로컬 저장: {docCount}개 문서 (브라우저 IndexedDB)</span>
                {docCount > 0 && (
                  <button
                    onClick={async () => {
                      setStatus('서버 동기화 중...');
                      try {
                        const docs = await getProjectDocuments(currentProject);
                        const syncDocs = docs
                          .filter(d => d.filename !== '__folder_placeholder__')
                          .map(d => ({ filename: d.filename, parsedText: d.parsedText }));
                        await api.syncTextsToServer(currentProject, syncDocs);
                        setStatus(`${syncDocs.length}개 문서 서버 동기화 완료.`);
                      } catch { setStatus('서버 동기화 실패.'); }
                    }}
                    className="px-2 py-0.5 bg-[#2383E2] text-white rounded hover:bg-[#1b6ec2] text-xs"
                  >
                    서버 동기화
                  </button>
                )}
              </div>
              <FilePicker onFilesSelected={handleUpload} loading={uploading} />
            </>
          ) : (
            <div className="flex items-center justify-center h-64 text-[#9B9A97] text-sm">
              프로젝트를 선택하거나 새로 생성하세요.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
