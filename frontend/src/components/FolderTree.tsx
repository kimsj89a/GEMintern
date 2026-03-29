import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';

interface FolderTreeProps {
  tree: Record<string, string[]>; // folder_name -> [doc_name, ...]
  projectName?: string;
  onDocClick?: (doc: string) => void;
  onDocDelete?: (doc: string) => void;
  onDocDownload?: (doc: string) => void;
  onFolderDelete?: (folder: string) => void;
  onDocMove?: (doc: string, targetFolder: string) => void;
  onBatchMove?: (docs: string[], targetFolder: string) => void;
  onCreateFolder?: (name: string) => void;
  selectable?: boolean;
  selectedDocs?: string[];
  onSelectionChange?: (selected: string[]) => void;
}

export default function FolderTree({
  tree, projectName, onDocClick, onDocDelete, onDocDownload, onFolderDelete, onDocMove, onBatchMove, onCreateFolder,
  selectable, selectedDocs = [], onSelectionChange,
}: FolderTreeProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    Object.keys(tree).forEach((f) => { init[f] = true; });
    return init;
  });
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; type: string; name: string } | null>(null);

  // Close context menu on outside click or scroll
  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    window.addEventListener('click', close);
    window.addEventListener('scroll', close, true);
    return () => {
      window.removeEventListener('click', close);
      window.removeEventListener('scroll', close, true);
    };
  }, [contextMenu]);

  const toggleFolder = (folder: string) => {
    setExpanded((prev) => ({ ...prev, [folder]: !prev[folder] }));
  };

  const toggleDoc = (doc: string) => {
    if (!onSelectionChange) return;
    const next = selectedDocs.includes(doc)
      ? selectedDocs.filter((d) => d !== doc)
      : [...selectedDocs, doc];
    onSelectionChange(next);
  };

  const toggleFolderDocs = (folder: string) => {
    if (!onSelectionChange) return;
    const docs = tree[folder] || [];
    const allSelected = docs.every((d) => selectedDocs.includes(d));
    if (allSelected) {
      onSelectionChange(selectedDocs.filter((d) => !docs.includes(d)));
    } else {
      const newSet = new Set([...selectedDocs, ...docs]);
      onSelectionChange([...newSet]);
    }
  };

  const handleContextMenu = (e: React.MouseEvent, type: string, name: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, type, name });
  };

  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [moveTarget, setMoveTarget] = useState<string | null>(null);

  const handleCreateFolder = () => {
    if (newFolderName.trim() && onCreateFolder) {
      onCreateFolder(newFolderName.trim());
      setNewFolderName('');
      setCreatingFolder(false);
    }
  };

  const folders = Object.keys(tree).sort((a, b) => {
    if (a === '__root__') return -1;
    if (b === '__root__') return 1;
    return a.localeCompare(b);
  });

  return (
    <div className="text-sm">
      {/* 폴더 추가 */}
      {onCreateFolder && (
        creatingFolder ? (
          <div className="flex items-center gap-1 px-2 py-1 mb-1">
            <input
              autoFocus
              value={newFolderName}
              onChange={e => setNewFolderName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleCreateFolder(); if (e.key === 'Escape') setCreatingFolder(false); }}
              placeholder="폴더명"
              className="flex-1 px-2 py-0.5 text-xs border border-slate-300 rounded focus:outline-none focus:border-blue-400"
            />
            <button onClick={handleCreateFolder} className="text-xs text-blue-600 hover:text-blue-700">확인</button>
            <button onClick={() => setCreatingFolder(false)} className="text-xs text-slate-400">취소</button>
          </div>
        ) : (
          <button
            onClick={() => setCreatingFolder(true)}
            className="flex items-center gap-1 px-2 py-1 mb-1 text-xs text-slate-400 hover:text-blue-600 transition-colors"
          >
            <span>+</span> 폴더 추가
          </button>
        )
      )}
      {/* 선택된 파일 일괄 이동 바 */}
      {selectable && selectedDocs.length > 0 && (onBatchMove || onDocMove) && (
        moveTarget !== null ? (
          <div className="flex items-center gap-1 px-2 py-1.5 mb-1 bg-blue-50 border border-blue-200 rounded-lg">
            <span className="text-xs text-blue-700 shrink-0">{selectedDocs.length}개 →</span>
            <select
              autoFocus
              value={moveTarget}
              onChange={e => setMoveTarget(e.target.value)}
              className="flex-1 px-1.5 py-0.5 text-xs border border-blue-300 rounded focus:outline-none"
            >
              <option value="__root__">루트</option>
              {Object.keys(tree).filter(f => f !== '__root__').sort().map(f => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
            <button
              onClick={() => {
                const target = moveTarget || '__root__';
                if (onBatchMove) {
                  onBatchMove(selectedDocs, target);
                } else if (onDocMove) {
                  selectedDocs.forEach(doc => onDocMove(doc, target));
                }
                setMoveTarget(null);
              }}
              className="px-2 py-0.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            >이동</button>
            <button onClick={() => setMoveTarget(null)} className="text-xs text-slate-400 hover:text-slate-600">취소</button>
          </div>
        ) : (
          <button
            onClick={() => setMoveTarget('__root__')}
            className="flex items-center gap-1 px-2 py-1 mb-1 text-xs text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
          >
            📁 선택 파일 이동 ({selectedDocs.length}개)
          </button>
        )
      )}
      {folders.map((folder) => {
        const docs = tree[folder] || [];
        const isRoot = folder === '__root__';
        const label = isRoot ? (projectName || '전체 문서') : folder;
        const isExpanded = expanded[folder] !== false;

        return (
          <div key={folder} className="mb-0.5">
            {/* Folder header */}
            <div
              className="flex items-center gap-1 px-2 py-1 rounded hover:bg-[#F7F6F3] cursor-pointer select-none group"
              onClick={() => toggleFolder(folder)}
              onContextMenu={(e) => !isRoot && handleContextMenu(e, 'folder', folder)}
            >
              <span className="text-xs text-[#9B9A97]">{isExpanded ? '▼' : '▶'}</span>
              {selectable && (
                <input
                  type="checkbox"
                  checked={docs.length > 0 && docs.every((d) => selectedDocs.includes(d))}
                  onChange={() => toggleFolderDocs(folder)}
                  onClick={(e) => e.stopPropagation()}
                  className="rounded"
                />
              )}
              <span className="text-[#787774]">📁</span>
              <span className="text-[#37352F] font-medium">{label}</span>
              <span className="text-xs text-[#9B9A97] ml-1">({docs.length})</span>
              {!isRoot && onFolderDelete && (
                <button
                  className="ml-auto text-[#9B9A97] hover:text-red-500 opacity-0 group-hover:opacity-100 text-xs"
                  onClick={(e) => { e.stopPropagation(); onFolderDelete(folder); }}
                >
                  ✕
                </button>
              )}
            </div>

            {/* Documents */}
            {isExpanded && (
              <div className="pl-5">
                {docs.map((doc) => (
                  <div
                    key={doc}
                    className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-[#F7F6F3] cursor-pointer group"
                    onClick={() => onDocClick?.(doc)}
                    onContextMenu={(e) => handleContextMenu(e, 'doc', doc)}
                  >
                    {selectable && (
                      <input
                        type="checkbox"
                        checked={selectedDocs.includes(doc)}
                        onChange={() => toggleDoc(doc)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded"
                      />
                    )}
                    <span className="text-[#9B9A97]">📄</span>
                    <span className="text-[#37352F] truncate flex-1" title={doc}>{doc}</span>
                    {onDocDelete && (
                      <button
                        className="text-[#9B9A97] hover:text-red-500 opacity-0 group-hover:opacity-100 text-xs"
                        onClick={(e) => { e.stopPropagation(); onDocDelete(doc); }}
                      >
                        🗑
                      </button>
                    )}
                  </div>
                ))}
                {docs.length === 0 && (
                  <div className="px-2 py-1 text-xs text-[#9B9A97] italic">비어있음</div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Context Menu — rendered via portal to avoid parent transform issues */}
      {contextMenu && createPortal(
        <div
          className="fixed bg-white border border-[#E9E9E7] rounded-lg shadow-lg py-1 z-[9999] text-sm"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {contextMenu.type === 'folder' && (
            <>
              <button className="w-full text-left px-4 py-1.5 hover:bg-[#F7F6F3]"
                onClick={() => { onFolderDelete?.(contextMenu.name); setContextMenu(null); }}>
                🗑 폴더 삭제
              </button>
            </>
          )}
          {contextMenu.type === 'doc' && (
            <>
              <button className="w-full text-left px-4 py-1.5 hover:bg-[#F7F6F3]"
                onClick={() => { onDocDownload?.(contextMenu.name); setContextMenu(null); }}>
                ⬇ 다운로드
              </button>
              <button className="w-full text-left px-4 py-1.5 hover:bg-[#F7F6F3]"
                onClick={() => { onDocDelete?.(contextMenu.name); setContextMenu(null); }}>
                🗑 문서 삭제
              </button>
              {Object.keys(tree).filter((f) => f !== '__root__').map((f) => (
                <button key={f} className="w-full text-left px-4 py-1.5 hover:bg-[#F7F6F3]"
                  onClick={() => { onDocMove?.(contextMenu.name, f); setContextMenu(null); }}>
                  📁 {f}로 이동
                </button>
              ))}
            </>
          )}
        </div>,
        document.body
      )}
    </div>
  );
}
