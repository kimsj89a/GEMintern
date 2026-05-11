import { useRef, useState, useCallback } from 'react';
import MarkdownViewer from '../components/MarkdownViewer';
import { extractTitle, copyRichText, downloadAsWord } from '../utils/clipboard';

const TOOLS: Record<string, { prefix: string; suffix: string; placeholder: string; block?: boolean }> = {
  bold: { prefix: '**', suffix: '**', placeholder: '볼드 텍스트' },
  italic: { prefix: '*', suffix: '*', placeholder: '이탤릭 텍스트' },
  strikethrough: { prefix: '~~', suffix: '~~', placeholder: '취소선 텍스트' },
  inlineCode: { prefix: '`', suffix: '`', placeholder: 'code' },
  link: { prefix: '[', suffix: '](url)', placeholder: '링크 텍스트' },
  h1: { prefix: '# ', suffix: '', placeholder: '제목 1', block: true },
  h2: { prefix: '## ', suffix: '', placeholder: '제목 2', block: true },
  h3: { prefix: '### ', suffix: '', placeholder: '제목 3', block: true },
  quote: { prefix: '> ', suffix: '', placeholder: '인용문', block: true },
  ul: { prefix: '- ', suffix: '', placeholder: '목록 항목', block: true },
  ol: { prefix: '1. ', suffix: '', placeholder: '목록 항목', block: true },
  hr: { prefix: '\n---\n', suffix: '', placeholder: '' },
  codeBlock: { prefix: '\n```\n', suffix: '\n```\n', placeholder: '코드를 입력하세요' },
  table: { prefix: '\n| 항목 | 설명 |\n|------|------|\n| ', suffix: ' | 내용 |\n', placeholder: '데이터' },
};
export default function MarkdownPage() {
  const [markdown, setMarkdown] = useState('');
  const [filename, setFilename] = useState('');
  const [copyMsg, setCopyMsg] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const applyTool = useCallback((toolKey: string) => {
    const ta = taRef.current;
    if (!ta) return;
    const tool = TOOLS[toolKey];
    if (!tool) return;

    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const text = ta.value;
    const selected = text.slice(start, end) || tool.placeholder;

    let prefix = tool.prefix;
    if (tool.block && start > 0 && text[start - 1] !== '\n') {
      prefix = '\n' + prefix;
    }

    const before = text.slice(0, start);
    const after = text.slice(end);
    const inserted = prefix + selected + tool.suffix;
    const newText = before + inserted + after;

    setMarkdown(newText);

    requestAnimationFrame(() => {
      ta.focus();
      const selStart = before.length + prefix.length;
      const selEnd = selStart + selected.length;
      ta.setSelectionRange(selStart, selEnd);
    });
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      if (e.key === 'b') { e.preventDefault(); applyTool('bold'); }
      else if (e.key === 'i') { e.preventDefault(); applyTool('italic'); }
      else if (e.key === 'k') { e.preventDefault(); applyTool('link'); }
    }
  }, [applyTool]);

  const handleFileOpen = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.md,.txt,.markdown';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      const text = await file.text();
      setMarkdown(text);
      setFilename(file.name.replace(/\.[^.]+$/, ''));
    };
    input.click();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['md', 'txt', 'markdown'].includes(ext || '')) {
      alert('마크다운(.md), 텍스트(.txt) 파일만 지원합니다.');
      return;
    }
    file.text().then((text) => {
      setMarkdown(text);
      setFilename(file.name.replace(/\.[^.]+$/, ''));
    });
  }, []);

  const handleCopy = useCallback(async () => {
    try {
      await copyRichText(markdown);
      setCopyMsg('✓ 복사됨');
      setTimeout(() => setCopyMsg(''), 2000);
    } catch {
      setCopyMsg('복사 실패');
      setTimeout(() => setCopyMsg(''), 2000);
    }
  }, [markdown]);

  const handleWord = useCallback(async () => {
    const fname = filename || extractTitle(markdown);
    try {
      await downloadAsWord(markdown, fname);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Word 변환 실패');
    }
  }, [markdown, filename]);

  const lineCount = markdown.split('\n').length;
  const charCount = markdown.length;
  const ToolBtn = ({ label, tool, className = '' }: { label: string; tool: string; className?: string }) => (
    <button
      type="button"
      onClick={() => applyTool(tool)}
      className={`px-2 py-1 text-xs rounded hover:bg-slate-200 transition-colors text-slate-600 ${className}`}
      title={tool}
    >
      {label}
    </button>
  );

  return (
    <div
      className={`h-full flex flex-col bg-white relative ${dragOver ? 'ring-2 ring-inset ring-blue-400' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={(e) => { if (e.currentTarget === e.target || !e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false); }}
      onDrop={handleDrop}
    >
      {dragOver && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-blue-50/80 backdrop-blur-[2px] pointer-events-none">
          <div className="text-base text-blue-500 font-medium px-6 py-3 bg-white rounded-xl shadow-lg border border-blue-200">
            📄 파일을 놓으면 마크다운을 불러옵니다
          </div>
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 gap-3 flex-wrap">
        <div className="min-w-0">
          <h1 className="text-base font-bold text-slate-800">Markdown 편집기</h1>
          <p className="text-xs text-slate-400 mt-0.5">마크다운 편집 + 실시간 미리보기 + 서식 복사 / Word 변환</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleCopy}
            disabled={!markdown}
            className="px-4 py-1.5 text-xs font-medium bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-300 text-white rounded-lg transition-colors"
          >
            서식 복사
          </button>
          {copyMsg && <span className="text-xs text-emerald-600">{copyMsg}</span>}
          <input
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="파일명"
            className="px-2 py-1 text-xs border border-slate-200 rounded-lg w-36 focus:outline-none focus:ring-1 focus:ring-blue-300"
          />
          <button
            onClick={handleWord}
            disabled={!markdown}
            className="px-4 py-1.5 text-xs font-medium bg-blue-500 hover:bg-blue-600 disabled:bg-slate-300 text-white rounded-lg transition-colors"
          >
            Word 변환
          </button>
          <span className="w-px h-4 bg-slate-200 mx-1" />
          <button
            onClick={handleFileOpen}
            className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
          >
            파일 열기
          </button>
          <button
            onClick={() => setMarkdown('')}
            className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
          >
            초기화
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-1 px-4 py-1.5 border-b border-slate-100 bg-slate-50/50 flex-wrap">
        <ToolBtn label="H1" tool="h1" className="font-bold" />
        <ToolBtn label="H2" tool="h2" className="font-bold" />
        <ToolBtn label="H3" tool="h3" className="font-bold" />
        <span className="w-px h-4 bg-slate-200 mx-1" />
        <ToolBtn label="B" tool="bold" className="font-bold" />
        <ToolBtn label="I" tool="italic" className="italic" />
        <ToolBtn label="S" tool="strikethrough" className="line-through" />
        <span className="w-px h-4 bg-slate-200 mx-1" />
        <ToolBtn label="링크" tool="link" />
        <ToolBtn label="Code" tool="inlineCode" />
        <ToolBtn label="```" tool="codeBlock" />
        <span className="w-px h-4 bg-slate-200 mx-1" />
        <ToolBtn label="• UL" tool="ul" />
        <ToolBtn label="1. OL" tool="ol" />
        <ToolBtn label="❝" tool="quote" />
        <span className="w-px h-4 bg-slate-200 mx-1" />
        <ToolBtn label="표" tool="table" />
        <ToolBtn label="─" tool="hr" />
      </div>
      {/* Split pane */}
      <div className="flex flex-1 min-h-0">
        {/* Editor */}
        <div className="w-1/2 flex flex-col border-r border-slate-200">
          <div className="px-3 py-1.5 text-[11px] text-slate-400 bg-slate-50 border-b border-slate-100 font-medium uppercase tracking-wider flex items-center justify-between">
            <span>편집</span>
            <span className="text-slate-300">{charCount}자 / {lineCount}행</span>
          </div>
          <textarea
            ref={taRef}
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 w-full resize-none p-4 text-sm text-slate-800 bg-white focus:outline-none"
            style={{ fontFamily: 'var(--font-mono, "Consolas", "Monaco", monospace)' }}
            placeholder="마크다운을 입력하세요... (파일을 드래그해서 놓을 수도 있습니다)"
            spellCheck={false}
          />
        </div>

        {/* Preview */}
        <div className="w-1/2 flex flex-col">
          <div className="px-3 py-1.5 text-[11px] text-slate-400 bg-slate-50 border-b border-slate-100 font-medium uppercase tracking-wider">
            미리보기
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <MarkdownViewer content={markdown} />
          </div>
        </div>
      </div>
    </div>
  );
}
