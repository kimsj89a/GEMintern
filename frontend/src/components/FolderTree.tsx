import { useState } from 'react';

interface FolderTreeProps {
  tree: Record<string, string[]>; // folder_name -> [doc_name, ...]
  projectName?: string;
  onDocClick?: (doc: string) => void;
  onDocDelete?: (doc: string) => void;
  onFolderDelete?: (folder: string) => void;
  onDocMove?: (doc: string, targetFolder: string) => void;
  selectable?: boolean;
  selectedDocs?: string[];
  onSelectionChange?: (selected: string[]) => void;
}

export default function FolderTree({
  tree, projectName, onDocClick, onDocDelete, onFolderDelete, onDocMove,
  selectable, selectedDocs = [], onSelectionChange,
}: FolderTreeProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    Object.keys(tree).forEach((f) => { init[f] = true; });
    return init;
  });
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; type: string; name: string } | null>(null);

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

  const folders = Object.keys(tree).sort((a, b) => {
    if (a === '__root__') return -1;
    if (b === '__root__') return 1;
    return a.localeCompare(b);
  });

  return (
    <div className="text-sm" onClick={() => setContextMenu(null)}>
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
                    <span className="text-[#37352F] truncate flex-1">{doc}</span>
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

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed bg-white border border-[#E9E9E7] rounded-lg shadow-lg py-1 z-50 text-sm"
          style={{ left: contextMenu.x, top: contextMenu.y }}
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
        </div>
      )}
    </div>
  );
}
