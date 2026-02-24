import { useRef, useState } from 'react';
import MarkdownViewer from '../components/MarkdownViewer';
import { extractTitle } from '../utils/clipboard';

export default function MarkdownPage() {
  const [inputMode, setInputMode] = useState<'file' | 'direct'>('direct');
  const [markdown, setMarkdown] = useState('');
  const [filename, setFilename] = useState('');
  const [userEditedFilename, setUserEditedFilename] = useState(false);
  const [preview, setPreview] = useState(false);
  const [converting, setConverting] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  /** 마크다운 내용에서 파일명 자동 생성 (사용자가 직접 수정하지 않은 경우) */
  const getEffectiveFilename = () => {
    if (userEditedFilename && filename) return filename;
    const title = extractTitle(markdown);
    return `${title}.docx`;
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setMarkdown(reader.result as string);
    reader.readAsText(file);
  };

  const handleConvert = async () => {
    if (!markdown.trim()) return;
    setConverting(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const effectiveName = getEffectiveFilename();
      const res = await fetch('/api/markdown-to-docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown, filename: effectiveName }),
        signal: controller.signal,
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = effectiveName; a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      if (err.name !== 'AbortError') alert(`변환 실패: ${err.message}`);
    }
    setConverting(false);
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setConverting(false);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">📝 Markdown → Word 변환</h1>
      <p className="text-sm text-[#787774] mb-6">마크다운 텍스트를 Word 문서로 변환합니다.</p>

      {/* Input mode */}
      <div className="flex gap-2 mb-4">
        <button onClick={() => setInputMode('direct')}
          className={`px-3 py-1.5 text-sm rounded-lg ${inputMode === 'direct' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          직접 입력
        </button>
        <button onClick={() => setInputMode('file')}
          className={`px-3 py-1.5 text-sm rounded-lg ${inputMode === 'file' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          파일 업로드
        </button>
      </div>

      {inputMode === 'file' && (
        <div className="mb-4">
          <label className="inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3]">
            📂 Markdown 파일 선택
            <input type="file" accept=".md,.txt" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>
      )}

      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <textarea
          value={markdown}
          onChange={(e) => setMarkdown(e.target.value)}
          placeholder="# 제목&#10;&#10;내용을 입력하세요..."
          rows={12}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm font-mono focus:outline-none focus:border-[#2383E2] resize-none"
        />
      </div>

      {/* Filename */}
      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-[#787774]">파일명:</label>
        <input
          value={filename}
          placeholder={extractTitle(markdown) + '.docx'}
          onChange={(e) => { setFilename(e.target.value); setUserEditedFilename(true); }}
          className="px-3 py-1.5 border border-[#E9E9E7] rounded-lg text-sm w-64 focus:outline-none focus:border-[#2383E2]"
        />
        {userEditedFilename && filename && (
          <button onClick={() => { setFilename(''); setUserEditedFilename(false); }}
            className="text-xs text-[#9B9A97] hover:text-[#37352F]">자동</button>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mb-4">
        <button onClick={() => setPreview(!preview)}
          className="px-4 py-2 border border-[#E9E9E7] text-sm rounded-lg hover:bg-[#F7F6F3]">
          👁️ {preview ? '미리보기 닫기' : '미리보기'}
        </button>
        {converting ? (
          <button onClick={handleStop}
            className="flex-1 py-2 bg-[#EB5757] text-white text-sm font-semibold rounded-lg hover:bg-[#d94848]">
            중지
          </button>
        ) : (
          <button onClick={handleConvert} disabled={!markdown.trim()}
            className="flex-1 py-2 bg-[#2383E2] text-white text-sm font-semibold rounded-lg hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0]">
            📄 Word 변환 및 저장
          </button>
        )}
      </div>

      {/* Preview */}
      {preview && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-6">
          <MarkdownViewer content={markdown} />
        </div>
      )}
    </div>
  );
}
