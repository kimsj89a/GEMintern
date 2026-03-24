import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';

interface Citation {
  id: number;
  source_doc: string;
  page: number | null;
  excerpt: string;
}

interface WikiSection {
  id: string;
  title: string;
  content: string;
  order: number;
  auto_generated: boolean;
  updated_at: string;
}

interface WikiData {
  sections: WikiSection[];
  citations: Citation[];
  generated_at: string | null;
}

// ── CitationTooltip ──

function CitationTooltip({
  citation,
  position,
  onDownload,
}: {
  citation: Citation;
  position: { x: number; y: number };
  onDownload: () => void;
}) {
  return (
    <div
      className="fixed z-50 w-72 bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs"
      style={{ left: position.x, top: position.y + 8 }}
    >
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-base">📄</span>
        <span className="font-semibold text-slate-700 truncate">{citation.source_doc.replace('.md', '')}</span>
        {citation.page != null && (
          <span className="text-slate-400 shrink-0">p.{citation.page}</span>
        )}
      </div>
      <div className="text-slate-500 leading-relaxed border-l-2 border-blue-200 pl-2 mb-2">
        "{citation.excerpt}"
      </div>
      <button
        onClick={onDownload}
        className="text-blue-500 hover:text-blue-700 text-[11px] font-medium"
      >
        원문 다운로드 →
      </button>
    </div>
  );
}

// ── CitationPreview modal ──

function CitationPreview({
  citation,
  onClose,
  onDownload,
}: {
  citation: Citation;
  onClose: () => void;
  onDownload: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-[480px] max-h-[70vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <span className="text-lg">📄</span>
            <span className="font-bold text-slate-800">{citation.source_doc.replace('.md', '')}</span>
            {citation.page != null && (
              <span className="text-sm text-slate-400">p.{citation.page}</span>
            )}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-lg">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
            {citation.excerpt}
          </div>
        </div>
        <div className="px-5 py-3 border-t border-slate-100 flex justify-end">
          <button
            onClick={onDownload}
            className="px-4 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            파일 다운로드
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Inline citation renderer ──

function RenderContent({
  content,
  citations,
  onCitationHover,
  onCitationClick,
}: {
  content: string;
  citations: Citation[];
  onCitationHover: (c: Citation, e: React.MouseEvent) => void;
  onCitationClick: (c: Citation) => void;
}) {
  // Split content by [n] patterns
  const parts = content.split(/(\[\d+\])/g);
  return (
    <span>
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (m) {
          const id = parseInt(m[1]);
          const cit = citations.find((c) => c.id === id);
          if (cit) {
            return (
              <sup
                key={i}
                className="inline-flex items-center justify-center w-4 h-4 text-[9px] font-bold text-blue-600 bg-blue-50 rounded cursor-pointer hover:bg-blue-100 mx-0.5"
                onMouseEnter={(e) => onCitationHover(cit, e)}
                onClick={() => onCitationClick(cit)}
              >
                {id}
              </sup>
            );
          }
        }
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}

// ── WikiSection component ──

function WikiSectionItem({
  section,
  citations,
  projectName,
  onUpdate,
  onDelete,
}: {
  section: WikiSection;
  citations: Citation[];
  projectName: string;
  onUpdate: () => void;
  onDelete: () => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(section.content);
  const [tooltip, setTooltip] = useState<{ citation: Citation; pos: { x: number; y: number } } | null>(null);
  const [preview, setPreview] = useState<Citation | null>(null);

  const handleSave = async () => {
    await api.patchWikiSection(projectName, section.id, { content: editContent });
    setEditing(false);
    onUpdate();
  };

  const handleDownload = (cit: Citation) => {
    api.downloadDoc(projectName, cit.source_doc);
  };

  return (
    <div className="border-b border-slate-100 last:border-b-0">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-50 transition-colors text-left"
      >
        <svg
          className={`w-3 h-3 text-slate-400 transition-transform ${collapsed ? '' : 'rotate-90'}`}
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
        <span className="text-xs font-semibold text-slate-700 flex-1">{section.title}</span>
        <button
          onClick={(e) => { e.stopPropagation(); setEditing(!editing); }}
          className="text-[10px] text-slate-400 hover:text-blue-500 px-1"
        >
          {editing ? '취소' : '편집'}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="text-[10px] text-slate-400 hover:text-red-500 px-1"
        >
          ✕
        </button>
      </button>

      {!collapsed && (
        <div className="px-3 pb-3">
          {editing ? (
            <div className="space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-32 text-xs border border-slate-200 rounded-lg p-2 focus:outline-none focus:border-blue-400 resize-y"
              />
              <button
                onClick={handleSave}
                className="px-3 py-1 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                저장
              </button>
            </div>
          ) : (
            <div
              className="text-xs text-slate-600 leading-relaxed"
              onMouseLeave={() => setTooltip(null)}
            >
              <RenderContent
                content={section.content}
                citations={citations}
                onCitationHover={(c, e) =>
                  setTooltip({ citation: c, pos: { x: e.clientX, y: e.clientY } })
                }
                onCitationClick={(c) => { setTooltip(null); setPreview(c); }}
              />
            </div>
          )}
        </div>
      )}

      {tooltip && (
        <CitationTooltip
          citation={tooltip.citation}
          position={tooltip.pos}
          onDownload={() => handleDownload(tooltip.citation)}
        />
      )}
      {preview && (
        <CitationPreview
          citation={preview}
          onClose={() => setPreview(null)}
          onDownload={() => handleDownload(preview)}
        />
      )}
    </div>
  );
}

// ── Main WikiPanel ──

export default function WikiPanel({ projectName }: { projectName: string }) {
  const [wiki, setWiki] = useState<WikiData | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addingSection, setAddingSection] = useState(false);
  const [newTitle, setNewTitle] = useState('');

  const loadWiki = useCallback(async () => {
    if (!projectName) return;
    setLoading(true);
    try {
      const data = await api.getWiki(projectName);
      setWiki(data?.generated_at ? data : null);
    } catch {
      setWiki(null);
    }
    setLoading(false);
  }, [projectName]);

  useEffect(() => { loadWiki(); }, [loadWiki]);

  const pollTask = useCallback(async (taskId: string) => {
    const poll = async () => {
      try {
        const status = await api.getTaskStatus(taskId);
        if (status.status === 'complete') {
          const result = status.result;
          if (result?.error) {
            setError(result.error);
          } else {
            setWiki(result);
          }
          setGenerating(false);
        } else if (status.status === 'error') {
          setError(status.error || '위키 생성 실패');
          setGenerating(false);
        } else {
          setTimeout(poll, 2000);
        }
      } catch {
        setError('상태 확인 실패');
        setGenerating(false);
      }
    };
    poll();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const { task_id } = await api.generateWiki(projectName);
      pollTask(task_id);
    } catch (e: any) {
      setError(e.message || '위키 생성 실패');
      setGenerating(false);
    }
  };

  const handleUpdate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const { task_id } = await api.updateWiki(projectName);
      pollTask(task_id);
    } catch (e: any) {
      setError(e.message || '위키 갱신 실패');
      setGenerating(false);
    }
  };

  const handleAddSection = async () => {
    if (!newTitle.trim()) return;
    const id = newTitle.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_가-힣]/g, '');
    await api.addWikiSection(projectName, { id: id || `custom_${Date.now()}`, title: newTitle.trim() });
    setNewTitle('');
    setAddingSection(false);
    loadWiki();
  };

  const handleDeleteSection = async (sectionId: string) => {
    if (!confirm('이 섹션을 삭제하시겠습니까?')) return;
    await api.deleteWikiSection(projectName, sectionId);
    loadWiki();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Empty state
  if (!wiki) {
    return (
      <div className="flex flex-col items-center py-6 px-4 text-center">
        <span className="text-3xl mb-2 opacity-50">📖</span>
        <span className="text-xs text-slate-500 mb-3">자료를 분석하여 위키를 생성합니다</span>
        {error && (
          <div className="text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-3 w-full">
            {error}
          </div>
        )}
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-4 py-1.5 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1.5"
        >
          {generating ? (
            <>
              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              생성 중...
            </>
          ) : (
            '위키 자동 생성'
          )}
        </button>
      </div>
    );
  }

  const sorted = [...wiki.sections].sort((a, b) => a.order - b.order);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-200">
        <span className="text-xs font-bold text-slate-700">위키</span>
        <button
          onClick={handleUpdate}
          disabled={generating}
          className="text-[10px] text-blue-500 hover:text-blue-700 disabled:opacity-50"
        >
          {generating ? '갱신 중...' : '위키 갱신'}
        </button>
      </div>

      {/* Sections */}
      <div className="flex-1 overflow-y-auto">
        {sorted.map((s) => (
          <WikiSectionItem
            key={s.id}
            section={s}
            citations={wiki.citations}
            projectName={projectName}
            onUpdate={loadWiki}
            onDelete={() => handleDeleteSection(s.id)}
          />
        ))}

        {/* Add section */}
        <div className="px-3 py-2">
          {addingSection ? (
            <div className="flex gap-1.5">
              <input
                autoFocus
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddSection()}
                placeholder="섹션 제목"
                className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-blue-400"
              />
              <button onClick={handleAddSection} className="px-2 py-1 text-xs bg-blue-500 text-white rounded-lg">추가</button>
              <button onClick={() => { setAddingSection(false); setNewTitle(''); }} className="px-2 py-1 text-xs text-slate-500 border rounded-lg">취소</button>
            </div>
          ) : (
            <button
              onClick={() => setAddingSection(true)}
              className="w-full text-center text-[11px] text-slate-400 hover:text-blue-500 py-1.5 border border-dashed border-slate-200 rounded-lg hover:border-blue-300"
            >
              + 섹션 추가
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
