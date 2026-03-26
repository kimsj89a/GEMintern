import { useRef, useState } from 'react';
import { api } from '../api/client';
import { subscribeTask, unsubscribeTask } from '../api/ws';
import FilePicker from '../components/FilePicker';
import MarkdownViewer from '../components/MarkdownViewer';
import { copyRichText, downloadAsWord, generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';
import GenerationProgress from '../components/GenerationProgress';

export default function DraftDocPage() {
  const { currentProject } = useAppStore();
  const [fileText, setFileText] = useState('');
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [uploadWarnings, setUploadWarnings] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [instruction, setInstruction] = useState('');
  const [generating, setGenerating] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [result, setResult] = useState('');
  const [genStartTime, setGenStartTime] = useState(0);
  const cancelRef = useRef(false);
  const activeTaskRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    try {
      const res = await api.freedocUpload(files);
      if (res.file_text) {
        setFileText((prev) => (prev ? prev + '\n\n' + res.file_text : res.file_text));
        setFileNames((prev) => [...prev, ...files.map((f) => f.name)]);
      }
      if (res.warnings && res.warnings.length > 0) {
        setUploadWarnings((prev) => [...prev, ...res.warnings]);
      }
    } catch {
      // ignore
    }
    setUploading(false);
  };

  const handleClearFiles = () => {
    setFileText('');
    setFileNames([]);
    setUploadWarnings([]);
  };

  const handleGenerate = async () => {
    if (!fileText.trim() && !pasteText.trim()) return;

    setGenerating(true);
    setStreamingText('');
    setResult('');
    setGenStartTime(Date.now());
    cancelRef.current = false;

    try {
      const { task_id } = await api.draftdocGenerate({
        file_text: fileText,
        paste_text: pasteText,
        instruction,
      });
      activeTaskRef.current = task_id;

      subscribeTask(task_id, (msg) => {
        if (cancelRef.current) { unsubscribeTask(task_id); return; }
        if (msg.type === 'chunk' && msg.data) {
          setStreamingText((prev) => prev + msg.data);
        } else if (msg.type === 'complete') {
          setResult(msg.result || '');
          setStreamingText('');
          setGenerating(false);
          unsubscribeTask(task_id);
        } else if (msg.type === 'error') {
          setResult(`오류: ${msg.error}`);
          setStreamingText('');
          setGenerating(false);
          unsubscribeTask(task_id);
        }
      });

      pollRef.current = setInterval(async () => {
        if (cancelRef.current) { if (pollRef.current) clearInterval(pollRef.current); return; }
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          if (pollRef.current) clearInterval(pollRef.current);
          setResult(status.result || '');
          setStreamingText('');
          setGenerating(false);
        } else if (status.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current);
          setResult(`오류: ${status.error}`);
          setStreamingText('');
          setGenerating(false);
        }
      }, 3000);
      setTimeout(() => { if (pollRef.current) clearInterval(pollRef.current); }, 600000);
    } catch (err: any) {
      setResult(`오류: ${err.message}`);
      setGenerating(false);
    }
  };

  const handleStop = () => {
    cancelRef.current = true;
    if (activeTaskRef.current) unsubscribeTask(activeTaskRef.current);
    if (pollRef.current) clearInterval(pollRef.current);
    if (streamingText) setResult(streamingText);
    setStreamingText('');
    setGenerating(false);
  };

  const handleReset = () => {
    setResult('');
    setStreamingText('');
  };

  const downloadMarkdown = () => {
    const text = result;
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = generateFilename('기안문', 'md', currentProject);
    a.click();
    URL.revokeObjectURL(url);
  };

  const displayText = streamingText || result;
  const hasSource = fileText.trim() || pasteText.trim();
  const canGenerate = hasSource && !generating;

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">기안문 작성</h1>
      <p className="text-sm text-[#787774] mb-6">
        자료를 업로드하면 AI가 공식 기안문(품의서/결재문서)을 작성합니다.
      </p>

      {displayText ? (
        <div className="space-y-4">
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-6">
            {generating && (
              <GenerationProgress
                streamingText={streamingText}
                startTime={genStartTime}
                onStop={handleStop}
              />
            )}
            {!generating && result && (
              <div className="flex gap-2 mb-4 pb-3 border-b border-[#E9E9E7]">
                <button onClick={() => copyRichText(result)}
                  className="px-3 py-1.5 text-xs bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 font-medium">
                  서식 복사
                </button>
                <button onClick={() => downloadAsWord(result, generateFilename('기안문', 'docx', currentProject))}
                  className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3]">
                  Word 저장
                </button>
                <button onClick={downloadMarkdown}
                  className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3]">
                  MD 저장
                </button>
                <div className="flex-1" />
                <button onClick={handleReset}
                  className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] text-[#9B9A97]">
                  새로 작성
                </button>
              </div>
            )}
            <div className="max-h-[60vh] overflow-y-auto">
              <MarkdownViewer content={displayText} />
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* File upload */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">1. 자료 업로드</label>
            <FilePicker onFilesSelected={handleUpload} loading={uploading} />
            {fileNames.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 items-center">
                {fileNames.map((name, i) => (
                  <span key={i} className="inline-flex items-center px-2.5 py-1 bg-[#E8F3FC] text-[#2383E2] text-xs rounded-lg">
                    {name}
                  </span>
                ))}
                <button onClick={handleClearFiles} className="text-xs text-[#EB5757] hover:underline ml-1">
                  전체 삭제
                </button>
              </div>
            )}
            {uploadWarnings.length > 0 && (
              <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                {uploadWarnings.map((w, i) => (
                  <p key={i}>{w}</p>
                ))}
              </div>
            )}
          </div>

          {/* Paste text */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">또는 텍스트 직접 붙여넣기</label>
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="여기에 텍스트를 붙여넣으세요..."
              rows={4}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
            />
          </div>

          {/* Additional instruction */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">2. 추가 요청사항 (선택)</label>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="예: 구체적인 수치를 강조해줘, 결재 요청 사유를 상세히 기술해줘..."
              rows={2}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
            />
          </div>

          {/* Generate button */}
          <button onClick={handleGenerate} disabled={!canGenerate}
            className={`w-full py-3 font-semibold rounded-xl transition-colors text-sm ${
              canGenerate
                ? 'bg-[#2383E2] text-white hover:bg-[#1b6ec2]'
                : 'bg-[#E9E9E7] text-[#9B9A97] cursor-not-allowed'
            }`}
          >
            기안문 생성
          </button>
        </div>
      )}
    </div>
  );
}
