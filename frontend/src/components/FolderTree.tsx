import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';

interface FolderTreeProps {
  tree: Record<string, string[]>;
  projectName?: string;
  onDocClick?: (doc: string) => void;
  onDocDelete?: (doc: string) => void;
  onDocDownload?: (doc: string) => void;
  onFolderDelete?: (folder: string) => void;
  onFolderRename?: (folder: string, newLeaf: string) => void;
  onDocMove?: (doc: string, targetFolder: string) => void;
  onBatchMove?: (docs: string[], targetFolder: string) => void;
  onCreateFolder?: (name: string) => void;
  selectable?: boolean;
  selectedDocs?: string[];
  onSelectionChange?: (selected: string[]) => void;
}

interface TreeNode {
  path: string;   // full key in tree dict, e.g. "finance/reports"
  label: string;  // last segment, e.g. "reports"
  docs: string[];
  children: TreeNode[];
}

function buildTree(flat: Record<string, string[]>): TreeNode[] {
  const paths = Object.keys(flat).filter(k => k !== '__root__').sort();
  const nodeMap = new Map<string, TreeNode>();
  for (const p of paths) {
    nodeMap.set(p, { path: p, label: p.split('/').at(-1)!, docs: flat[p] || [], children: [] });
  }
  const top: TreeNode[] = [];
  for (const p of paths) {
    const parts = p.split('/');
    if (parts.length === 1) {
      top.push(nodeMap.get(p)!);
    } else {
      const parentPath = parts.slice(0, -1).join('/');
      const parent = nodeMap.get(parentPath);
      if (parent) parent.children.push(nodeMap.get(p)!);
      else top.push(nodeMap.get(p)!); // orphan subfolder → promote to top
    }
  }
  return top;
}

export default function FolderTree({
  tree, projectName, onDocClick, onDocDelete, onDocDownload,
  onFolderDelete, onFolderRename, onDocMove, onBatchMove, onCreateFolder,
  selectable, selectedDocs = [], onSelectionChange,
}: FolderTreeProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [contextMenu, setContextMenu] = useState<{
    x: number; y: number; type: 'folder' | 'doc' | 'empty'; name: string;
  } | null>(null);
  const [renamingFolder, setRenamingFolder] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [creatingIn, setCreatingIn] = useState<string | null>(null); // '__root__' or folder path
  const [newFolderName, setNewFolderName] = useState('');
  const [dragDocs, setDragDocs] = useState<string[]>([]);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const dragImageRef = useRef<HTMLDivElement | null>(null);
  const lastClickedRef = useRef<string | null>(null);

  // Auto-expand new folders
  useEffect(() => {
    setExpanded(prev => {
      const next = { ...prev };
      Object.keys(tree).forEach(f => { if (!(f in next)) next[f] = true; });
      return next;
    });
  }, [tree]);

  // Close context menu on outside click/scroll
  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    window.addEventListener('click', close);
    window.addEventListener('scroll', close, true);
    return () => { window.removeEventListener('click', close); window.removeEventListener('scroll', close, true); };
  }, [contextMenu]);

  const flatDocs = useCallback(() => {
    const result: string[] = [];
    const sorted = Object.keys(tree).sort((a, b) => a === '__root__' ? -1 : b === '__root__' ? 1 : a.localeCompare(b));
    for (const f of sorted) for (const d of (tree[f] || [])) result.push(d);
    return result;
  }, [tree]);

  const handleDocClick = (doc: string, e: React.MouseEvent) => {
    if (!onSelectionChange) return;
    if (e.shiftKey && lastClickedRef.current) {
      const all = flatDocs();
      const a = all.indexOf(lastClickedRef.current), b = all.indexOf(doc);
      if (a >= 0 && b >= 0) {
        onSelectionChange([...new Set([...selectedDocs, ...all.slice(Math.min(a, b), Math.max(a, b) + 1)])]);
      }
    } else {
      const next = selectedDocs.includes(doc) ? selectedDocs.filter(d => d !== doc) : [...selectedDocs, doc];
      onSelectionChange(next);
    }
    lastClickedRef.current = doc;
  };

  const toggleFolderDocs = (folder: string) => {
    if (!onSelectionChange) return;
    // Collect docs from this folder AND all subfolders (paths starting with folder/)
    const allDocs: string[] = [...(tree[folder] || [])];
    if (folder !== '__root__') {
      const prefix = folder + '/';
      for (const [key, docs] of Object.entries(tree)) {
        if (key.startsWith(prefix)) allDocs.push(...docs);
      }
    } else {
      // Root: select ALL docs in all folders
      for (const docs of Object.values(tree)) allDocs.push(...docs);
    }
    const unique = [...new Set(allDocs)];
    if (unique.length > 0 && unique.every(d => selectedDocs.includes(d)))
      onSelectionChange(selectedDocs.filter(d => !unique.includes(d)));
    else
      onSelectionChange([...new Set([...selectedDocs, ...unique])]);
  };

  // ── DnD ──
  const handleDragStart = (e: React.DragEvent, doc: string) => {
    const docs = selectedDocs.includes(doc) && selectedDocs.length > 1 ? [...selectedDocs] : [doc];
    setDragDocs(docs);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', JSON.stringify(docs));
    const el = document.createElement('div');
    el.style.cssText = 'position:fixed;top:-1000px;left:-1000px;padding:6px 12px;background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;font-size:12px;color:#1D4ED8;white-space:nowrap;z-index:99999;pointer-events:none';
    el.textContent = docs.length > 1 ? `📄 ${docs.length}개 파일` : `📄 ${doc}`;
    document.body.appendChild(el);
    dragImageRef.current = el;
    e.dataTransfer.setDragImage(el, 0, 0);
    setTimeout(() => { if (dragImageRef.current) { document.body.removeChild(dragImageRef.current); dragImageRef.current = null; } }, 0);
  };

  const handleDragEnd = () => {
    setDragDocs([]); setDropTarget(null);
    if (dragImageRef.current) { try { document.body.removeChild(dragImageRef.current); } catch {} dragImageRef.current = null; }
  };

  const handleFolderDrop = (e: React.DragEvent, targetFolder: string) => {
    e.preventDefault(); setDropTarget(null);
    const docs = dragDocs.length > 0 ? dragDocs : (() => { try { return JSON.parse(e.dataTransfer.getData('text/plain')); } catch { return []; } })();
    setDragDocs([]);
    if (!docs.length) return;
    const toMove = docs.filter((d: string) => !(tree[targetFolder] || []).includes(d));
    if (!toMove.length) return;
    if (onBatchMove) onBatchMove(toMove, targetFolder);
    else if (onDocMove) toMove.forEach((d: string) => onDocMove(d, targetFolder));
  };

  const docFolderMap = useCallback(() => {
    const map: Record<string, string> = {};
    for (const [f, docs] of Object.entries(tree)) for (const d of docs) map[d] = f;
    return map;
  }, [tree]);

  // ── Folder / doc creation & rename ──
  const handleCreateFolder = () => {
    if (!newFolderName.trim() || !onCreateFolder) return;
    const fullName = creatingIn && creatingIn !== '__root__'
      ? `${creatingIn}/${newFolderName.trim()}`
      : newFolderName.trim();
    onCreateFolder(fullName);
    setNewFolderName(''); setCreatingIn(null);
  };

  const handleRenameConfirm = () => {
    if (!renamingFolder) return;
    const v = renameValue.trim();
    if (v) onFolderRename?.(renamingFolder, v);
    setRenamingFolder(null);
  };

  const isDragging = dragDocs.length > 0;
  const topNodes = buildTree(tree);
  const allFolderPaths = Object.keys(tree).filter(k => k !== '__root__');

  // Inline folder-create input
  const CreateInput = ({ parentPath }: { parentPath: string }) => {
    if (creatingIn !== parentPath) return null;
    return (
      <div className="flex items-center gap-1 px-2 py-1">
        <input autoFocus value={newFolderName}
          onChange={e => setNewFolderName(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleCreateFolder(); if (e.key === 'Escape') setCreatingIn(null); }}
          placeholder={parentPath !== '__root__' ? '하위 폴더명' : '폴더명'}
          className="flex-1 px-2 py-0.5 text-xs border border-blue-300 rounded focus:outline-none focus:border-blue-500"
        />
        <button onClick={handleCreateFolder} className="text-xs text-blue-600 hover:text-blue-800">확인</button>
        <button onClick={() => setCreatingIn(null)} className="text-xs text-slate-400">취소</button>
      </div>
    );
  };

  // Doc row
  const renderDoc = (doc: string, indent = 0) => {
    const isDrag = dragDocs.includes(doc);
    return (
      <div key={doc} draggable
        onDragStart={e => handleDragStart(e, doc)}
        onDragEnd={handleDragEnd}
        style={{ paddingLeft: indent + 8 }}
        className={`flex items-center gap-1 pr-2 py-0.5 rounded cursor-grab group transition-all ${
          isDrag ? 'opacity-40 bg-blue-50' : 'hover:bg-[#F7F6F3]'
        } ${selectedDocs.includes(doc) && !isDrag ? 'bg-blue-50/50' : ''}`}
        onClick={e => { e.stopPropagation(); if (selectable) handleDocClick(doc, e); else onDocClick?.(doc); }}
        onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setContextMenu({ x: e.clientX, y: e.clientY, type: 'doc', name: doc }); }}
      >
        {selectable && (
          <input type="checkbox" checked={selectedDocs.includes(doc)} onChange={() => {}}
            onClick={e => e.stopPropagation()} className="rounded pointer-events-none" readOnly />
        )}
        <span className="text-[#9B9A97] text-xs shrink-0">📄</span>
        <span className="text-[#37352F] truncate flex-1 text-xs" title={doc}>{doc}</span>
        {onDocDelete && !isDragging && (
          <button className="text-[#9B9A97] hover:text-red-500 opacity-0 group-hover:opacity-100 text-xs shrink-0"
            onClick={e => { e.stopPropagation(); onDocDelete(doc); }}>🗑</button>
        )}
      </div>
    );
  };

  // Recursive folder node renderer
  const renderFolder = (node: TreeNode, indent = 0): React.ReactNode => {
    const isExp = expanded[node.path] !== false;
    const isDropHov = dropTarget === node.path && isDragging;
    const isRenaming = renamingFolder === node.path;

    return (
      <div key={node.path}>
        <div
          style={{ paddingLeft: indent + 8 }}
          className={`flex items-center gap-1 pr-2 py-1 rounded cursor-pointer group transition-colors ${
            isDropHov ? 'bg-blue-100 border border-blue-300 border-dashed' : 'hover:bg-[#F7F6F3] border border-transparent'
          }`}
          onClick={() => setExpanded(p => ({ ...p, [node.path]: !isExp }))}
          onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setContextMenu({ x: e.clientX, y: e.clientY, type: 'folder', name: node.path }); }}
          onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDropTarget(node.path); }}
          onDragLeave={e => { if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as HTMLElement)) setDropTarget(null); }}
          onDrop={e => handleFolderDrop(e, node.path)}
        >
          <span className="text-xs text-[#9B9A97] shrink-0">{isExp ? '▼' : '▶'}</span>
          {selectable && (
            <input type="checkbox"
              checked={node.docs.length > 0 && node.docs.every(d => selectedDocs.includes(d))}
              onChange={() => toggleFolderDocs(node.path)}
              onClick={e => e.stopPropagation()}
              className="rounded"
            />
          )}
          <span className="shrink-0">{isDropHov ? '📂' : '📁'}</span>
          {isRenaming ? (
            <input autoFocus value={renameValue}
              onChange={e => setRenameValue(e.target.value)}
              onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') handleRenameConfirm(); if (e.key === 'Escape') setRenamingFolder(null); }}
              onBlur={handleRenameConfirm}
              onClick={e => e.stopPropagation()}
              className="flex-1 min-w-0 px-1 py-0 text-xs border border-blue-400 rounded focus:outline-none bg-white"
            />
          ) : (
            <span className={`font-medium text-xs truncate flex-1 ${isDropHov ? 'text-blue-700' : 'text-[#37352F]'}`}>{node.label}</span>
          )}
          <span className="text-xs text-[#9B9A97] shrink-0">({node.docs.length})</span>
        </div>

        {isExp && (
          <div onDragOver={e => { e.preventDefault(); setDropTarget(node.path); }} onDrop={e => handleFolderDrop(e, node.path)}>
            <CreateInput parentPath={node.path} />
            {node.children.map(child => renderFolder(child, indent + 12))}
            {node.docs.map(doc => renderDoc(doc, indent + 12))}
            {node.docs.length === 0 && node.children.length === 0 && creatingIn !== node.path && !isDragging && (
              <div style={{ paddingLeft: indent + 20 }} className="py-1 text-xs text-[#9B9A97] italic">비어있음</div>
            )}
            {isDragging && isDropHov && node.docs.length === 0 && (
              <div style={{ paddingLeft: indent + 20 }} className="py-2 mx-2 text-xs italic rounded border border-dashed text-blue-600 border-blue-300 bg-blue-50">여기에 놓기</div>
            )}
          </div>
        )}
      </div>
    );
  };

  const rootDocs = tree['__root__'] || [];
  const rootExp = expanded['__root__'] !== false;
  const rootDropHov = dropTarget === '__root__' && isDragging;

  return (
    <div
      className="text-sm select-none min-h-[80px]"
      onContextMenu={e => { e.preventDefault(); setContextMenu({ x: e.clientX, y: e.clientY, type: 'empty', name: '' }); }}
    >
      {/* Root section */}
      <div>
        <div
          className={`flex items-center gap-1 px-2 py-1 rounded cursor-pointer group transition-colors ${
            rootDropHov ? 'bg-blue-100 border border-blue-300 border-dashed' : 'hover:bg-[#F7F6F3] border border-transparent'
          }`}
          onClick={() => setExpanded(p => ({ ...p, __root__: !rootExp }))}
          onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setContextMenu({ x: e.clientX, y: e.clientY, type: 'empty', name: '' }); }}
          onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDropTarget('__root__'); }}
          onDragLeave={e => { if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as HTMLElement)) setDropTarget(null); }}
          onDrop={e => handleFolderDrop(e, '__root__')}
        >
          <span className="text-xs text-[#9B9A97]">{rootExp ? '▼' : '▶'}</span>
          {selectable && (
            <input type="checkbox"
              checked={rootDocs.length > 0 && rootDocs.every(d => selectedDocs.includes(d))}
              onChange={() => toggleFolderDocs('__root__')}
              onClick={e => e.stopPropagation()}
              className="rounded"
            />
          )}
          <span>{rootDropHov ? '📂' : '📁'}</span>
          <span className="font-medium text-xs text-[#37352F] flex-1">{projectName || '전체 문서'}</span>
          <span className="text-xs text-[#9B9A97]">({rootDocs.length})</span>
        </div>

        {rootExp && (
          <div className="pl-2"
            onDragOver={e => { e.preventDefault(); setDropTarget('__root__'); }}
            onDrop={e => handleFolderDrop(e, '__root__')}
          >
            <CreateInput parentPath="__root__" />
            {topNodes.map(n => renderFolder(n, 4))}
            {rootDocs.map(doc => renderDoc(doc, 4))}
          </div>
        )}
      </div>

      {isDragging && (
        <div className="mt-2 px-2 py-1.5 text-xs text-blue-500 bg-blue-50 rounded-lg text-center border border-blue-200">
          📁 폴더 위에 놓아서 이동
        </div>
      )}

      {/* Context Menu */}
      {contextMenu && createPortal(
        <div ref={el => {
          // Auto-reposition if menu overflows viewport
          if (!el) return;
          const rect = el.getBoundingClientRect();
          if (rect.bottom > window.innerHeight) el.style.top = `${contextMenu.y - rect.height}px`;
          if (rect.right > window.innerWidth) el.style.left = `${contextMenu.x - rect.width}px`;
        }}
          className="fixed bg-white border border-[#E9E9E7] rounded-xl shadow-xl py-1.5 z-[9999] min-w-[168px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={e => e.stopPropagation()}
        >
          {/* Empty area */}
          {contextMenu.type === 'empty' && onCreateFolder && (
            <button className="w-full text-left px-4 py-2 text-sm hover:bg-[#F7F6F3] flex items-center gap-2"
              onClick={() => { setCreatingIn('__root__'); setNewFolderName(''); setContextMenu(null); }}>
              📁 폴더 추가
            </button>
          )}

          {/* Folder */}
          {contextMenu.type === 'folder' && (
            <>
              {onCreateFolder && (
                <button className="w-full text-left px-4 py-2 text-sm hover:bg-[#F7F6F3] flex items-center gap-2"
                  onClick={() => { setCreatingIn(contextMenu.name); setNewFolderName(''); setContextMenu(null); }}>
                  📁 하위 폴더 추가
                </button>
              )}
              {onFolderRename && (
                <button className="w-full text-left px-4 py-2 text-sm hover:bg-[#F7F6F3] flex items-center gap-2"
                  onClick={() => {
                    setRenamingFolder(contextMenu.name);
                    setRenameValue(contextMenu.name.split('/').at(-1) || contextMenu.name);
                    setContextMenu(null);
                  }}>
                  ✏️ 이름 변경
                </button>
              )}
              {onFolderDelete && (
                <>
                  <div className="border-t border-[#E9E9E7] my-1" />
                  <button className="w-full text-left px-4 py-2 text-sm hover:bg-red-50 text-red-600 flex items-center gap-2"
                    onClick={() => { onFolderDelete(contextMenu.name); setContextMenu(null); }}>
                    🗑 폴더 삭제
                  </button>
                </>
              )}
            </>
          )}

          {/* Doc */}
          {contextMenu.type === 'doc' && (
            <>
              {onDocDownload && (
                <button className="w-full text-left px-4 py-2 text-sm hover:bg-[#F7F6F3] flex items-center gap-2"
                  onClick={() => { onDocDownload(contextMenu.name); setContextMenu(null); }}>
                  ⬇ 다운로드
                </button>
              )}
              {allFolderPaths.length > 0 && onDocMove && (() => {
                const curFolder = docFolderMap()[contextMenu.name];
                const targets = allFolderPaths.filter(f => f !== curFolder).sort();
                const hasRoot = curFolder !== '__root__';
                const batchDocs = selectedDocs.length > 1 ? selectedDocs : [];

                const FolderBtn = ({ folder, onClick }: { folder: string; onClick: () => void }) => {
                  const depth = (folder.match(/\//g) || []).length;
                  const label = folder.split('/').at(-1)!;
                  return (
                    <button className="w-full text-left py-1.5 text-sm hover:bg-[#F7F6F3] flex items-center gap-1"
                      style={{ paddingLeft: 16 + depth * 8 }}
                      onClick={onClick}>
                      <span className="text-xs shrink-0">📁</span>
                      <span className="text-xs truncate">{label}</span>
                      {depth > 0 && <span className="text-[10px] text-slate-400 shrink-0 ml-1">{folder}</span>}
                    </button>
                  );
                };

                return (
                  <>
                    {/* 이 파일만 이동 */}
                    <div className="border-t border-[#E9E9E7] my-1" />
                    <div className="px-4 py-1 text-[11px] text-[#9B9A97] font-medium">이 파일만 이동</div>
                    {hasRoot && (
                      <button className="w-full text-left px-4 py-1.5 text-sm hover:bg-[#F7F6F3]"
                        onClick={() => { onDocMove(contextMenu.name, '__root__'); setContextMenu(null); }}>
                        <span className="text-xs">📁 루트</span>
                      </button>
                    )}
                    {targets.map(f => (
                      <FolderBtn key={f} folder={f} onClick={() => { onDocMove(contextMenu.name, f); setContextMenu(null); }} />
                    ))}

                    {/* 선택 파일 일괄 이동 */}
                    {batchDocs.length > 0 && (
                      <>
                        <div className="border-t border-[#E9E9E7] my-1" />
                        <div className="px-4 py-1 text-[11px] text-[#9B9A97] font-medium">선택 파일 일괄 이동 ({batchDocs.length}개)</div>
                        {hasRoot && (
                          <button className="w-full text-left px-4 py-1.5 text-sm hover:bg-[#F7F6F3]"
                            onClick={() => {
                              if (onBatchMove) onBatchMove(batchDocs, '__root__');
                              else batchDocs.forEach(d => onDocMove(d, '__root__'));
                              setContextMenu(null);
                            }}>
                            <span className="text-xs">📁 루트</span>
                          </button>
                        )}
                        {targets.map(f => (
                          <FolderBtn key={f} folder={f} onClick={() => {
                            if (onBatchMove) onBatchMove(batchDocs, f);
                            else batchDocs.forEach(d => onDocMove(d, f));
                            setContextMenu(null);
                          }} />
                        ))}
                      </>
                    )}
                  </>
                );
              })()}
              {onDocDelete && (
                <>
                  <div className="border-t border-[#E9E9E7] my-1" />
                  <button className="w-full text-left px-4 py-2 text-sm hover:bg-red-50 text-red-600 flex items-center gap-2"
                    onClick={() => { onDocDelete(contextMenu.name); setContextMenu(null); }}>
                    🗑 삭제
                  </button>
                </>
              )}
            </>
          )}
        </div>,
        document.body
      )}
    </div>
  );
}
