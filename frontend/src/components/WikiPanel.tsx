import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { marked } from 'marked';
import { api } from '../api/client';
import { downloadAsWord, downloadAsMd } from '../utils/clipboard';

interface Citation {
  id: number;
  source_doc: string;
  page: number | null;
  excerpt: string;
  heading?: string | null;
  context?: string | null;
  context_excerpt_range?: [number, number] | null;
  position?: number | null;
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
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-base">📄</span>
        <span className="font-semibold text-slate-700 truncate">{citation.source_doc.replace('.md', '')}</span>
        {citation.page != null && (
          <span className="text-slate-400 shrink-0">p.{citation.page}</span>
        )}
      </div>
      {citation.heading && (
        <div className="text-[10px] text-slate-400 mb-1.5 truncate">📍 {citation.heading}</div>
      )}
      <div className="text-slate-500 leading-relaxed border-l-2 border-blue-200 pl-2 mb-2">
        "{citation.excerpt}"
      </div>
      <button
        onClick={onDownload}
        className="text-blue-500 hover:text-blue-700 text-[11px] font-medium"
      >
        클릭하여 원문 위치 확인 →
      </button>
    </div>
  );
}

// ── CitationPreview modal ──

function CitationPreview({
  citation,
  enrichedContext,
  loadingContext,
  onClose,
  onDownload,
}: {
  citation: Citation;
  enrichedContext?: { context: string; context_excerpt_range: [number, number]; heading?: string; position?: number; page?: number } | null;
  loadingContext?: boolean;
  onClose: () => void;
  onDownload: () => void;
}) {
  const ctx = enrichedContext || (citation.context ? {
    context: citation.context,
    context_excerpt_range: citation.context_excerpt_range!,
    heading: citation.heading,
    position: citation.position,
    page: citation.page,
  } : null);
  const heading = ctx?.heading || citation.heading;
  const page = ctx?.page ?? citation.page;
  const position = ctx?.position ?? citation.position;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-[520px] max-h-[75vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <span className="text-lg">📄</span>
            <span className="font-bold text-slate-800">{citation.source_doc.replace('.md', '')}</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-lg">✕</button>
        </div>

        {/* Location bar */}
        <div className="px-5 py-2 bg-slate-50 border-b border-slate-100 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
          {heading && <span className="flex items-center gap-1"><span>📍</span><span className="font-medium text-slate-600">{heading}</span></span>}
          {page != null && <span>p.{page}</span>}
          {position != null && <span>문서의 약 {position}% 위치</span>}
          {!heading && page == null && position == null && !loadingContext && <span className="text-slate-400">위치 정보 없음</span>}
          {loadingContext && <span className="text-slate-400">위치 검색 중...</span>}
        </div>

        {/* Context body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loadingContext ? (
            <div className="flex items-center justify-center py-6">
              <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : ctx?.context && ctx.context_excerpt_range ? (
            <div className="text-[13px] text-slate-600 leading-relaxed whitespace-pre-wrap bg-slate-50 rounded-lg p-4 border border-slate-200">
              <span className="text-slate-400">…</span>
              {ctx.context.slice(0, ctx.context_excerpt_range[0])}
              <mark className="bg-yellow-200/70 text-slate-800 px-0.5 rounded-sm">{ctx.context.slice(ctx.context_excerpt_range[0], ctx.context_excerpt_range[1])}</mark>
              {ctx.context.slice(ctx.context_excerpt_range[1])}
              <span className="text-slate-400">…</span>
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
              "{citation.excerpt}"
            </div>
          )}
        </div>

        {/* Footer */}
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

function CitationBadge({
  id,
  citation,
  onHover,
  onClick,
}: {
  id: number;
  citation: Citation;
  onHover: (c: Citation, e: React.MouseEvent) => void;
  onClick: (c: Citation) => void;
}) {
  return (
    <sup
      className="inline-flex items-center justify-center min-w-[16px] h-4 px-0.5 text-[9px] font-bold text-blue-600 bg-blue-50 rounded cursor-pointer hover:bg-blue-100 mx-0.5"
      onMouseEnter={(e) => onHover(citation, e)}
      onClick={() => onClick(citation)}
    >
      {id}
    </sup>
  );
}

function RenderContent({
  content,
  citations,
  onCitationHover,
  onCitationClick,
  fontSize,
}: {
  content: string;
  citations: Citation[];
  onCitationHover: (c: Citation, e: React.MouseEvent) => void;
  onCitationClick: (c: Citation) => void;
  fontSize?: number;
}) {
  const fs = fontSize || 14;
  return (
    <ReactMarkdown
      remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{injectCitations(children)}</p>,
        li: ({ children }) => <li>{injectCitations(children)}</li>,
        td: ({ children }) => {
          const text = String(children ?? '').trim();
          const isNumeric = /^[\d,.\-+%()₩$€¥ ]+$/.test(text) && /\d/.test(text);
          return <td className={`border border-slate-200 px-2 py-1 ${isNumeric ? 'text-right tabular-nums' : ''}`}>{injectCitations(children)}</td>;
        },
        th: ({ children }) => <th className="border border-slate-200 px-2 py-1 bg-slate-50 font-semibold">{injectCitations(children)}</th>,
        table: ({ children }) => <table style={{ fontSize: fs }} className="w-full border-collapse border border-slate-200 my-2">{children}</table>,
        thead: ({ children }) => <thead>{children}</thead>,
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => <tr className="even:bg-slate-50">{children}</tr>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        del: ({ children }) => <span>~{children}~</span>,
        h1: ({ children }) => <h3 style={{ fontSize: fs + 4 }} className="font-bold mt-3 mb-1">{children}</h3>,
        h2: ({ children }) => <h3 style={{ fontSize: fs + 4 }} className="font-bold mt-3 mb-1">{children}</h3>,
        h3: ({ children }) => <h4 style={{ fontSize: fs + 2 }} className="font-semibold mt-2 mb-1">{children}</h4>,
        ul: ({ children }) => <ul className="list-disc pl-4 my-1 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 my-1 space-y-0.5">{children}</ol>,
      }}
    >
      {content}
    </ReactMarkdown>
  );

  function injectCitations(children: React.ReactNode): React.ReactNode {
    if (!children) return children;
    if (typeof children === 'string') {
      return splitCitations(children);
    }
    if (Array.isArray(children)) {
      return children.map((child, i) => {
        if (typeof child === 'string') return <span key={i}>{splitCitations(child)}</span>;
        return child;
      });
    }
    return children;
  }

  function splitCitations(text: string): React.ReactNode {
    const parts = text.split(/(\[\d+(?:,\s*\d+)*\])/g);
    return parts.map((part, i) => {
      // Match single [n] or grouped [n, m, ...]
      const m = part.match(/^\[([\d,\s]+)\]$/);
      if (m) {
        const ids = m[1].split(',').map((s) => parseInt(s.trim()));
        return (
          <span key={i}>
            {ids.map((id) => {
              const cit = citations.find((c) => c.id === id);
              if (cit) {
                return <CitationBadge key={id} id={id} citation={cit} onHover={onCitationHover} onClick={onCitationClick} />;
              }
              return <sup key={id} className="text-[9px] text-slate-400">[{id}]</sup>;
            })}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  }
}

// ── WikiSection component ──

function WikiSectionItem({
  section,
  citations,
  projectName,
  selectedDocs,
  onUpdate,
  onDelete,
  fontSize,
}: {
  section: WikiSection;
  citations: Citation[];
  projectName: string;
  selectedDocs?: string[];
  onUpdate: () => void;
  onDelete: () => void;
  fontSize: number;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(section.content);
  const [editTitle, setEditTitle] = useState(section.title);
  const [revising, setRevising] = useState(false);
  const [reviseInput, setReviseInput] = useState('');
  const [reviseLoading, setReviseLoading] = useState(false);
  const [tooltip, setTooltip] = useState<{ citation: Citation; pos: { x: number; y: number } } | null>(null);
  const [preview, setPreview] = useState<Citation | null>(null);
  const [enrichedContext, setEnrichedContext] = useState<any>(null);
  const [loadingContext, setLoadingContext] = useState(false);

  // Fetch context on-demand when preview opens
  useEffect(() => {
    if (!preview) {
      setEnrichedContext(null);
      return;
    }
    // Already has context embedded
    if (preview.context && preview.context_excerpt_range) return;
    setLoadingContext(true);
    api.getCitationContext(projectName, preview.source_doc, preview.excerpt)
      .then((data: any) => { if (data.found) setEnrichedContext(data); })
      .catch(() => {})
      .finally(() => setLoadingContext(false));
  }, [preview, projectName]);

  const handleSave = async () => {
    await api.patchWikiSection(projectName, section.id, {
      content: editContent,
      ...(editTitle !== section.title ? { title: editTitle } : {}),
    });
    setEditing(false);
    onUpdate();
  };

  const handleRevise = async () => {
    if (!reviseInput.trim()) return;
    setReviseLoading(true);
    try {
      const { task_id } = await api.reviseWikiSection(projectName, section.id, reviseInput, selectedDocs);
      const poll = async () => {
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          if (status.result?.error) {
            alert(`수정 실패: ${status.result.error}`);
          } else {
            onUpdate();
            setRevising(false);
            setReviseInput('');
          }
          setReviseLoading(false);
        } else if (status.status === 'error') {
          alert(`오류: ${status.error || '알 수 없는 오류'}`);
          setReviseLoading(false);
        } else {
          setTimeout(poll, 2000);
        }
      };
      poll();
    } catch {
      setReviseLoading(false);
    }
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
          onClick={(e) => { e.stopPropagation(); setRevising(!revising); setEditing(false); }}
          className="text-[10px] text-slate-400 hover:text-purple-500 px-1"
        >
          {revising ? '취소' : 'AI 수정'}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); setEditing(!editing); setRevising(false); }}
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
              <input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full text-sm font-semibold border border-slate-200 rounded-lg px-2 py-1 focus:outline-none focus:border-blue-400"
                placeholder="섹션 제목"
              />
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
          ) : revising ? (
            <div className="space-y-2">
              <div className="flex gap-1.5">
                <input
                  autoFocus
                  value={reviseInput}
                  onChange={(e) => setReviseInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleRevise()}
                  placeholder="수정 지시 (예: 표로 정리해줘, 더 간결하게)"
                  className="flex-1 px-2 py-1.5 text-xs border border-purple-200 rounded-lg focus:outline-none focus:border-purple-400"
                  disabled={reviseLoading}
                />
                <button
                  onClick={handleRevise}
                  disabled={reviseLoading || !reviseInput.trim()}
                  className="px-3 py-1.5 text-xs bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 flex items-center gap-1"
                >
                  {reviseLoading ? (
                    <><div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> 수정 중...</>
                  ) : 'AI 수정'}
                </button>
              </div>
              <div
                style={{ fontSize }}
                className="text-slate-600 leading-relaxed"
                onMouseLeave={() => setTooltip(null)}
              >
                <RenderContent
                  content={section.content}
                  citations={citations}
                  fontSize={fontSize}
                  onCitationHover={(c, e) =>
                    setTooltip({ citation: c, pos: { x: e.clientX, y: e.clientY } })
                  }
                  onCitationClick={(c) => { setTooltip(null); setPreview(c); }}
                />
              </div>
            </div>
          ) : (
            <div
              style={{ fontSize }}
              className="text-slate-600 leading-relaxed"
              onMouseLeave={() => setTooltip(null)}
            >
              <RenderContent
                content={section.content}
                citations={citations}
                fontSize={fontSize}
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
          enrichedContext={enrichedContext}
          loadingContext={loadingContext}
          onClose={() => setPreview(null)}
          onDownload={() => handleDownload(preview)}
        />
      )}
    </div>
  );
}

// ── Main WikiPanel ──

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function WikiPanel({ projectName, selectedDocs }: { projectName: string; selectedDocs?: string[] }) {
  const [wiki, setWiki] = useState<WikiData | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addingSection, setAddingSection] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [fontSize, setFontSize] = useState(14);
  const [showExport, setShowExport] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  const loadWiki = useCallback(async () => {
    if (!projectName) return;
    setLoading(true);
    try {
      const data = await api.getWiki(projectName);
      setWiki(data?.sections?.length > 0 ? data : null);
    } catch {
      setWiki(null);
    }
    setLoading(false);
  }, [projectName]);

  useEffect(() => { loadWiki(); }, [loadWiki]);

  const pollTask = useCallback(async (taskId: string) => {
    const startTime = Date.now();
    const TIMEOUT = 180_000; // 3분
    const poll = async () => {
      if (Date.now() - startTime > TIMEOUT) {
        setError('위키 생성 시간 초과 (3분). 문서가 너무 많으면 일부만 선택해 주세요.');
        setGenerating(false);
        return;
      }
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
      const { task_id } = await api.generateWiki(projectName, selectedDocs);
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
      const { task_id } = await api.updateWiki(projectName, selectedDocs);
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

  // Close export dropdown on outside click
  useEffect(() => {
    if (!showExport) return;
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setShowExport(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showExport]);

  const exportAsHtml = () => {
    if (!wiki) return;
    const sorted = [...wiki.sections].sort((a, b) => a.order - b.order);
    const body = sorted.map(s => `<h2>${s.title}</h2>\n${marked(s.content)}`).join('\n<hr>\n');
    const html = `<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>Wiki – ${projectName}</title>
<style>
body{font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;max-width:800px;margin:0 auto;padding:40px 24px;color:#222;line-height:1.7}
h2{margin-top:32px;padding-bottom:6px;border-bottom:1px solid #e2e8f0}
table{border-collapse:collapse;width:100%;margin:12px 0}
th,td{border:1px solid #cbd5e1;padding:6px 10px;text-align:left}
th{background:#f1f5f9;font-weight:600}
tr:nth-child(even){background:#f8fafc}
hr{border:none;border-top:1px solid #e2e8f0;margin:24px 0}
ul,ol{padding-left:1.5em}
</style></head><body>
<h1>📖 ${projectName} Wiki</h1>
${body}
<footer style="margin-top:48px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8">
Generated by GEMintern · ${new Date().toLocaleDateString('ko-KR')}
</footer>
</body></html>`;
    downloadBlob(new Blob([html], { type: 'text/html;charset=utf-8' }), `wiki-${projectName}.html`);
    setShowExport(false);
  };

  const wikiToMarkdown = () => {
    if (!wiki) return '';
    const stripRefs = (text: string) => text.replace(/\s*\[\d+(?:,\s*\d+)*\]/g, '');
    const sorted = [...wiki.sections].sort((a, b) => a.order - b.order);
    return `# ${projectName} Wiki\n\n` +
      sorted.map(s => `## ${s.title}\n\n${stripRefs(s.content)}`).join('\n\n---\n\n');
  };

  const exportAsWord = () => {
    if (!wiki) return;
    downloadAsWord(wikiToMarkdown(), `wiki_${projectName}`);
    setShowExport(false);
  };

  const exportAsMd = () => {
    if (!wiki) return;
    downloadAsMd(wikiToMarkdown(), `wiki_${projectName}`);
    setShowExport(false);
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
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200">
        <span className="text-xs font-bold text-slate-700">위키</span>
        {/* Font size control */}
        <div className="flex items-center gap-0.5 ml-1">
          <button
            onClick={() => setFontSize(s => Math.max(10, s - 1))}
            className="w-5 h-5 flex items-center justify-center text-[10px] text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded"
            title="글씨 축소"
          >A-</button>
          <span className="text-[9px] text-slate-400 w-5 text-center tabular-nums">{fontSize}</span>
          <button
            onClick={() => setFontSize(s => Math.min(22, s + 1))}
            className="w-5 h-5 flex items-center justify-center text-[10px] text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded"
            title="글씨 확대"
          >A+</button>
        </div>
        <div className="flex-1" />
        {/* Export dropdown */}
        <div ref={exportRef} className="relative">
          <button
            onClick={() => setShowExport(!showExport)}
            className="text-[10px] text-slate-500 hover:text-slate-700 px-1.5 py-0.5 rounded hover:bg-slate-100"
          >
            내보내기 ▾
          </button>
          {showExport && (
            <div className="absolute right-0 top-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-30 py-1 min-w-[140px]">
              <button
                onClick={exportAsHtml}
                className="w-full text-left px-3 py-1.5 text-[11px] text-slate-700 hover:bg-slate-50"
              >
                HTML로 내보내기
              </button>
              <button
                onClick={exportAsMd}
                className="w-full text-left px-3 py-1.5 text-[11px] text-slate-700 hover:bg-slate-50"
              >
                MD로 내보내기
              </button>
              <button
                onClick={exportAsWord}
                className="w-full text-left px-3 py-1.5 text-[11px] text-slate-700 hover:bg-slate-50"
              >
                Word로 내보내기
              </button>
            </div>
          )}
        </div>
        <button
          onClick={handleUpdate}
          disabled={generating}
          className="text-[10px] text-blue-500 hover:text-blue-700 disabled:opacity-50"
        >
          {generating ? '갱신 중...' : '위키 갱신'}
        </button>
      </div>

      {/* Sections — draggable to reorder */}
      <div className="flex-1 overflow-y-auto">
        {sorted.map((s, idx) => (
          <div key={s.id}
            draggable
            onDragStart={e => { e.dataTransfer.setData('text/plain', String(idx)); (e.currentTarget as HTMLElement).style.opacity = '0.4'; }}
            onDragEnd={e => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
            onDragOver={e => { e.preventDefault(); (e.currentTarget as HTMLElement).style.borderTop = '2px solid #6366f1'; }}
            onDragLeave={e => { (e.currentTarget as HTMLElement).style.borderTop = ''; }}
            onDrop={async e => {
              e.preventDefault();
              (e.currentTarget as HTMLElement).style.borderTop = '';
              const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
              if (fromIdx === idx || isNaN(fromIdx)) return;
              // Reorder: update order values
              const reordered = [...sorted];
              const [moved] = reordered.splice(fromIdx, 1);
              reordered.splice(idx, 0, moved);
              // Update order on each section
              for (let i = 0; i < reordered.length; i++) {
                if (reordered[i].order !== i) {
                  await api.patchWikiSection(projectName, reordered[i].id, { order: i });
                }
              }
              loadWiki();
            }}
          >
            <WikiSectionItem
              section={s}
              citations={wiki.citations}
              projectName={projectName}
              selectedDocs={selectedDocs}
              onUpdate={loadWiki}
              onDelete={() => handleDeleteSection(s.id)}
              fontSize={fontSize}
            />
          </div>
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
