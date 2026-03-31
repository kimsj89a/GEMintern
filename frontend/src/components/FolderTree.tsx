import { useState, useEffect, useRef, useCallback } from 'react';
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

  // Drag-and-drop state
  const [dragDocs, setDragDocs] = useState<string[]>([]);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const dragImageRef = useRef<HTMLDivElement | null>(null);

  // Shift-click range selection
  const lastClickedRef = useRef<string | null>(null);

  // Expand new folders
  useEffect(() => {
    setExpanded(prev => {
      const next = { ...prev };
      for (const f of Object.keys(tree)) {
        if (!(f in next)) next[f] = true;
      }
      return next;
    });
  }, [tree]);

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

  // Build flat doc list for shift-click range selection
  const flatDocs = useCallback(() => {
    const result: string[] = [];
    const folders = Object.keys(tree).sort((a, b) => {
      if (a === '__root__') return -1;
      if (b === '__root__') return 1;
      return a.localeCompare(b);
    });
    for (const f of folders) {
      for (const d of (tree[f] || [])) {
        result.push(d);
      }
    }
    return result;
  }, [tree]);

  const handleDocClick = (doc: string, e: React.MouseEvent) => {
    if (!onSelectionChange) return;

    if (e.shiftKey && lastClickedRef.current) {
      // Range select
      const all = flatDocs();
      const lastIdx = all.indexOf(lastClickedRef.current);
      const curIdx = all.indexOf(doc);
      if (lastIdx >= 0 && curIdx >= 0) {
        const start = Math.min(lastIdx, curIdx);
        const end = Math.max(lastIdx, curIdx);
        const range = all.slice(start, end + 1);
        const newSet = new Set([...selectedDocs, ...range]);
        onSelectionChange([...newSet]);
      }
    } else if (e.ctrlKey || e.metaKey) {
      // Toggle single
      const next = selectedDocs.includes(doc)
        ? selectedDocs.filter((d) => d !== doc)
        : [...selectedDocs, doc];
      onSelectionChange(next);
    } else {
      // Toggle single (checkbox behavior)
      const next = selectedDocs.includes(doc)
        ? selectedDocs.filter((d) => d !== doc)
        : [...selectedDocs, doc];
      onSelectionChange(next);
    }
    lastClickedRef.current = doc;
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

  const handleCreateFolder = () => {
    if (newFolderName.trim() && onCreateFolder) {
      onCreateFolder(newFolderName.trim());
      setNewFolderName('');
      setCreatingFolder(false);
    }
  };

  // ── Drag-and-drop handlers ──

  const handleDragStart = (e: React.DragEvent, doc: string) => {
    // If dragged doc is already selected, drag all selected; otherwise just this one
    let docs: string[];
    if (selectedDocs.includes(doc) && selectedDocs.length > 1) {
      docs = [...selectedDocs];
    } else {
      docs = [doc];
    }
    setDragDocs(docs);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', JSON.stringify(docs));

    // Custom drag image
    const el = document.createElement('div');
    el.style.cssText = 'position:fixed;top:-1000px;left:-1000px;padding:6px 12px;background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;font-size:12px;color:#1D4ED8;white-space:nowrap;z-index:99999;pointer-events:none';
    el.textContent = docs.length > 1 ? `📄 ${docs.length}개 파일` : `📄 ${doc}`;
    document.body.appendChild(el);
    dragImageRef.current = el;
    e.dataTransfer.setDragImage(el, 0, 0);

    // Cleanup drag image after a short delay
    setTimeout(() => {
      if (dragImageRef.current) {
        document.body.removeChild(dragImageRef.current);
        dragImageRef.current = null;
      }
    }, 0);
  };

  const handleDragEnd = () => {
    setDragDocs([]);
    setDropTarget(null);
    if (dragImageRef.current) {
      try { document.body.removeChild(dragImageRef.current); } catch {}
      dragImageRef.current = null;
    }
  };

  const handleFolderDragOver = (e: React.DragEvent, folder: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDropTarget(folder);
  };

  const handleFolderDragLeave = (e: React.DragEvent) => {
    // Only clear if actually leaving the folder (not entering a child)
    const related = e.relatedTarget as HTMLElement | null;
    if (related && (e.currentTarget as HTMLElement).contains(related)) return;
    setDropTarget(null);
  };

  const handleFolderDrop = (e: React.DragEvent, targetFolder: string) => {
    e.preventDefault();
    setDropTarget(null);
    const docs = dragDocs.length > 0 ? dragDocs : (() => {
      try { return JSON.parse(e.dataTransfer.getData('text/plain')); } catch { return []; }
    })();
    setDragDocs([]);

    if (!docs.length) return;

    // Filter out docs already in target folder
    const targetDocs = tree[targetFolder] || [];
    const docsToMove = docs.filter((d: string) => !targetDocs.includes(d));
    if (!docsToMove.length) return;

    if (onBatchMove) {
      onBatchMove(docsToMove, targetFolder);
    } else if (onDocMove) {
      docsToMove.forEach((d: string) => onDocMove(d, targetFolder));
    }
  };

  // ── Find which folder a doc is in ──
  const docFolderMap = useCallback(() => {
    const map: Record<string, string> = {};
    for (const [folder, docs] of Object.entries(tree)) {
      for (const d of docs) { map[d] = folder; }
    }
    return map;
  }, [tree]);

  const folders = Object.keys(tree).sort((a, b) => {
    if (a === '__root__') return -1;
    if (b === '__root__') return 1;
    return a.localeCompare(b);
  });

  const isDragging = dragDocs.length > 0;

  return (
    <div className="text-sm select-none">
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
      {folders.map((folder) => {
        const docs = tree[folder] || [];
        const isRoot = folder === '__root__';
        const label = isRoot ? (projectName || '전체 문서') : folder;
        const isExpanded = expanded[folder] !== false;
        const isDropHover = dropTarget === folder && isDragging;

        return (
          <div key={folder} className="mb-0.5">
            {/* Folder header — drop zone */}
            <div
              className={`flex items-center gap-1 px-2 py-1 rounded cursor-pointer group transition-colors ${
                isDropHover
                  ? 'bg-blue-100 border border-blue-300 border-dashed'
                  : 'hover:bg-[#F7F6F3] border border-transparent'
              }`}
              onClick={() => toggleFolder(folder)}
              onContextMenu={(e) => !isRoot && handleContextMenu(e, 'folder', folder)}
              onDragOver={(e) => handleFolderDragOver(e, folder)}
              onDragLeave={handleFolderDragLeave}
              onDrop={(e) => handleFolderDrop(e, folder)}
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
              <span className={isDropHover ? 'text-blue-600' : 'text-[#787774]'}>
                {isDropHover ? '📂' : '📁'}
              </span>
              <span className={`font-medium ${isDropHover ? 'text-blue-700' : 'text-[#37352F]'}`}>{label}</span>
              <span className="text-xs text-[#9B9A97] ml-1">({docs.length})</span>
              {!isRoot && onFolderDelete && !isDragging && (
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
              <div
                className="pl-5"
                onDragOver={(e) => handleFolderDragOver(e, folder)}
                onDrop={(e) => handleFolderDrop(e, folder)}
              >
                {docs.map((doc) => {
                  const isBeingDragged = dragDocs.includes(doc);
                  return (
                    <div
                      key={doc}
                      draggable
                      onDragStart={(e) => handleDragStart(e, doc)}
                      onDragEnd={handleDragEnd}
                      className={`flex items-center gap-1 px-2 py-0.5 rounded cursor-grab group transition-all ${
                        isBeingDragged ? 'opacity-40 bg-blue-50' : 'hover:bg-[#F7F6F3]'
                      } ${selectedDocs.includes(doc) && !isBeingDragged ? 'bg-blue-50/50' : ''}`}
                      onClick={(e) => {
                        if (selectable) handleDocClick(doc, e);
                        else onDocClick?.(doc);
                      }}
                      onContextMenu={(e) => handleContextMenu(e, 'doc', doc)}
                    >
                      {selectable && (
                        <input
                          type="checkbox"
                          checked={selectedDocs.includes(doc)}
                          onChange={() => {}}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded pointer-events-none"
                          readOnly
                        />
                      )}
                      <span className="text-[#9B9A97]">📄</span>
                      <span className="text-[#37352F] truncate flex-1" title={doc}>{doc}</span>
                      {onDocDelete && !isDragging && (
                        <button
                          className="text-[#9B9A97] hover:text-red-500 opacity-0 group-hover:opacity-100 text-xs"
                          onClick={(e) => { e.stopPropagation(); onDocDelete(doc); }}
                        >
                          🗑
                        </button>
                      )}
                    </div>
                  );
                })}
                {docs.length === 0 && !isDragging && (
                  <div className="px-2 py-1 text-xs text-[#9B9A97] italic">비어있음</div>
                )}
                {docs.length === 0 && isDragging && (
                  <div className={`px-2 py-2 text-xs italic rounded border border-dashed transition-colors ${
                    isDropHover ? 'text-blue-600 border-blue-300 bg-blue-50' : 'text-[#9B9A97] border-slate-200'
                  }`}>
                    여기에 놓기
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Drag hint */}
      {isDragging && (
        <div className="mt-2 px-2 py-1.5 text-xs text-blue-500 bg-blue-50 rounded-lg text-center border border-blue-200">
          📁 폴더 위에 놓아서 이동
        </div>
      )}

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
              {Object.keys(tree).filter((f) => {
                // Only show folders the doc is NOT currently in
                const currentFolder = docFolderMap()[contextMenu.name];
                return f !== currentFolder;
              }).sort().map((f) => (
                <button key={f} className="w-full text-left px-4 py-1.5 hover:bg-[#F7F6F3]"
                  onClick={() => { onDocMove?.(contextMenu.name, f); setContextMenu(null); }}>
                  📁 {f === '__root__' ? '루트' : f}로 이동
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
