import { useRef, useState } from 'react';
import { api } from '../api/client';
import { subscribeTask, unsubscribeTask } from '../api/ws';
import FilePicker from '../components/FilePicker';
import MarkdownViewer from '../components/MarkdownViewer';
import { copyRichText, downloadAsWord, generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';
import GenerationProgress from '../components/GenerationProgress';

const PRESETS: { label: string; value: string }[] = [
  { label: '자유 요약', value: '제공된 자료를 종합적으로 분석하여 핵심 내용을 체계적으로 요약 정리해주세요.' },
  { label: '보고서', value: '제공된 자료를 바탕으로 업무 보고서 형태로 작성해주세요. 배경, 현황, 분석, 시사점 순서로 구성해주세요.' },
  { label: '비교 분석', value: '제공된 자료들을 비교 분석하여 공통점, 차이점, 주요 시사점을 정리해주세요.' },
  { label: '회의록 정리', value: '제공된 자료(회의 내용)를 회의록 형태로 정리해주세요. 일시, 참석자, 안건, 논의사항, 결정사항, 후속조치 순서로 작성해주세요.' },
  { label: '직접 입력', value: '' },
];

export default function FreeDocPage() {
  const { currentProject } = useAppStore();
  const [fileText, setFileText] = useState('');
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [preset, setPreset] = useState(0);
  const [instruction, setInstruction] = useState(PRESETS[0].value);
  const [generating, setGenerating] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [result, setResult] = useState('');
  const [genStartTime, setGenStartTime] = useState(0);
  const cancelRef = useRef(false);
  const activeTaskRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handlePresetChange = (idx: number) => {
    setPreset(idx);
    setInstruction(PRESETS[idx].value);
  };

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    try {
      const res = await api.freedocUpload(files);
      if (res.file_text) {
        setFileText((prev) => (prev ? prev + '\n\n' + res.file_text : res.file_text));
        setFileNames((prev) => [...prev, ...files.map((f) => f.name)]);
      }
    } catch {
      // ignore
    }
    setUploading(false);
  };

  const handleClearFiles = () => {
    setFileText('');
    setFileNames([]);
  };

  const handleGenerate = async () => {
    if (!instruction.trim()) return;
    if (!fileText.trim() && !pasteText.trim()) return;

    setGenerating(true);
    setStreamingText('');
    setResult('');
    setGenStartTime(Date.now());
    cancelRef.current = false;

    try {
      const { task_id } = await api.freedocGenerate({
        instruction,
        file_text: fileText,
        paste_text: pasteText,
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

      // Fallback polling
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
    a.download = generateFilename('자유양식문서', 'md', currentProject);
    a.click();
    URL.revokeObjectURL(url);
  };

  const displayText = streamingText || result;
  const hasSource = fileText.trim() || pasteText.trim();
  const canGenerate = instruction.trim() && hasSource && !generating;

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">📝 자유양식 문서 작성</h1>
      <p className="text-sm text-[#787774] mb-6">
        프로젝트 선택 없이 파일을 올리고 지시사항만 주면 AI가 문서를 작성합니다.
      </p>

      {/* Result view */}
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
                <button onClick={() => downloadAsWord(result, generateFilename('자유양식문서', 'docx', currentProject))}
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
                  새 문서 작성
                </button>
              </div>
            )}
            <div className="max-h-[60vh] overflow-y-auto">
              <MarkdownViewer content={displayText} />
            </div>
          </div>
        </div>
      ) : (
        /* Input view */
        <div className="space-y-4">
          {/* File upload */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">1. 자료 업로드</label>
            <FilePicker onFilesSelected={handleUpload} loading={uploading} />
            {fileNames.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 items-center">
                {fileNames.map((name, i) => (
                  <span key={i} className="inline-flex items-center px-2.5 py-1 bg-[#E8F3FC] text-[#2383E2] text-xs rounded-lg">
                    📄 {name}
                  </span>
                ))}
                <button onClick={handleClearFiles} className="text-xs text-[#EB5757] hover:underline ml-1">
                  전체 삭제
                </button>
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

          {/* Instruction */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">2. 지시사항</label>
            <div className="flex flex-wrap gap-2 mb-3">
              {PRESETS.map((p, i) => (
                <button key={i} onClick={() => handlePresetChange(i)}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                    preset === i
                      ? 'border-[#2383E2] bg-[#E8F3FC] text-[#2383E2]'
                      : 'border-[#E9E9E7] hover:bg-[#F7F6F3]'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="예: 이 자료를 바탕으로 투자 검토 요약서를 작성해주세요..."
              rows={3}
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
            🚀 문서 작성 시작
          </button>
        </div>
      )}
    </div>
  );
}
