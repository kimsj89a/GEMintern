import { useRef, useState } from 'react';
import { api } from '../api/client';
import FilePicker from '../components/FilePicker';
import MarkdownViewer from '../components/MarkdownViewer';

const MODE_OPTIONS = [
  { value: 'full', label: '전체 업데이트', desc: '문서 전체를 검토하여 업데이트' },
  { value: 'partial', label: '부분 업데이트', desc: '지시한 부분만 선택적으로 수정' },
];

const PRESETS = [
  { label: '최신 데이터 반영', value: '추가 자료의 최신 데이터를 반영하여 기존 문서의 수치와 내용을 업데이트해주세요.' },
  { label: '추가 자료 통합', value: '추가 자료의 내용을 기존 문서에 적절한 위치에 통합하여 반영해주세요.' },
  { label: '오류 수정', value: '기존 문서의 오류나 부정확한 내용을 추가 자료를 참고하여 수정해주세요.' },
  { label: '직접 입력', value: '' },
];

type DocInfo = {
  session_id: string;
  filename: string;
  doc_type: string;
  paragraph_count: number;
  preview: string;
};

type UpdateResult = {
  output_path: string;
  output_filename: string;
  summary: string;
  preview: string;
};

export default function DocUpdaterPage() {
  // Step 1: Original document
  const [docInfo, setDocInfo] = useState<DocInfo | null>(null);
  const [uploadingOriginal, setUploadingOriginal] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Step 2: Supplementary
  const [supFileNames, setSupFileNames] = useState<string[]>([]);
  const [uploadingSup, setUploadingSup] = useState(false);
  const [pasteText, setPasteText] = useState('');

  // Step 3: Instruction
  const [preset, setPreset] = useState(0);
  const [instruction, setInstruction] = useState(PRESETS[0].value);
  const [mode, setMode] = useState('full');

  // Generation
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<UpdateResult | null>(null);
  const [error, setError] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleUploadOriginal = async (files: File[]) => {
    if (files.length === 0) return;
    setUploadingOriginal(true);
    setError('');
    try {
      const res = await api.docUpdaterUploadOriginal(files[0]);
      if (res.error) {
        setError(res.error);
      } else {
        setDocInfo(res);
      }
    } catch (err: any) {
      setError(err.message);
    }
    setUploadingOriginal(false);
  };

  const handleUploadSupplementary = async (files: File[]) => {
    if (!docInfo) return;
    setUploadingSup(true);
    try {
      const res = await api.docUpdaterUploadSupplementary(docInfo.session_id, files);
      if (res.filenames) {
        setSupFileNames((prev) => [...prev, ...res.filenames]);
      }
    } catch {
      // ignore
    }
    setUploadingSup(false);
  };

  const handlePresetChange = (idx: number) => {
    setPreset(idx);
    setInstruction(PRESETS[idx].value);
  };

  const handleRun = async () => {
    if (!docInfo || !instruction.trim()) return;
    setGenerating(true);
    setResult(null);
    setError('');

    try {
      const { task_id } = await api.docUpdaterRun({
        session_id: docInfo.session_id,
        supplementary_text: pasteText,
        instruction,
        mode,
      });

      pollRef.current = setInterval(async () => {
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          if (pollRef.current) clearInterval(pollRef.current);
          try {
            const parsed = JSON.parse(status.result);
            setResult(parsed);
          } catch {
            setError('결과 파싱 오류');
          }
          setGenerating(false);
        } else if (status.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current);
          setError(status.error || '알 수 없는 오류');
          setGenerating(false);
        }
      }, 2000);

      // Safety timeout: 10 minutes
      setTimeout(() => {
        if (pollRef.current) clearInterval(pollRef.current);
      }, 600000);
    } catch (err: any) {
      setError(err.message);
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    api.docUpdaterDownload(result.output_path, result.output_filename);
  };

  const handleReset = () => {
    setDocInfo(null);
    setSupFileNames([]);
    setPasteText('');
    setPreset(0);
    setInstruction(PRESETS[0].value);
    setMode('full');
    setResult(null);
    setError('');
    setGenerating(false);
    if (pollRef.current) clearInterval(pollRef.current);
  };

  const canRun = docInfo && instruction.trim() && !generating;

  // Result view
  if (result) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <h1 className="text-xl font-bold text-[#37352F] mb-1">
          🔄 문서 업데이트 완료
        </h1>
        <p className="text-sm text-[#787774] mb-6">
          {docInfo?.filename} → {result.output_filename}
        </p>

        <div className="space-y-4">
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-6">
            <MarkdownViewer content={result.preview} />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleDownload}
              className="px-4 py-2 bg-[#2383E2] text-white text-sm font-medium rounded-lg hover:bg-[#1b6ec2] transition-colors"
            >
              📥 업데이트된 문서 다운로드
            </button>
            <button
              onClick={handleReset}
              className="px-4 py-2 border border-[#E9E9E7] text-sm rounded-lg hover:bg-[#F7F6F3]"
            >
              🔄 새 문서 업데이트
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">
        🔄 문서 업데이트
      </h1>
      <p className="text-sm text-[#787774] mb-6">
        기존 문서의 서식을 보존하면서 추가 자료를 반영하여 내용을 업데이트합니다.
      </p>

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {/* Step 1: Original document */}
        <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
          <label className="block text-sm font-medium text-[#37352F] mb-2">
            1. 원본 문서 업로드
          </label>
          <p className="text-xs text-[#787774] mb-3">
            업데이트할 원본 문서를 올려주세요. (docx, pptx, txt, md, pdf)
          </p>
          {docInfo ? (
            <div>
              <div className="flex items-center gap-3 px-3 py-2.5 bg-[#F0FFF4] border border-green-200 rounded-lg">
                <span className="text-green-600 text-lg">✅</span>
                <div className="flex-1">
                  <span className="text-sm font-medium text-[#37352F]">
                    {docInfo.filename}
                  </span>
                  <span className="ml-2 text-xs text-[#787774]">
                    ({docInfo.doc_type} / {docInfo.paragraph_count}개 문단)
                  </span>
                </div>
                <button
                  onClick={() => setShowPreview(!showPreview)}
                  className="text-xs text-[#2383E2] hover:underline"
                >
                  {showPreview ? '프리뷰 닫기' : '프리뷰 보기'}
                </button>
                <button
                  onClick={() => {
                    setDocInfo(null);
                    setSupFileNames([]);
                  }}
                  className="text-xs text-[#EB5757] hover:underline"
                >
                  변경
                </button>
              </div>
              {showPreview && (
                <pre className="mt-2 p-3 bg-[#F7F6F3] border border-[#E9E9E7] rounded-lg text-xs text-[#37352F] max-h-48 overflow-y-auto whitespace-pre-wrap">
                  {docInfo.preview}
                </pre>
              )}
            </div>
          ) : (
            <FilePicker
              onFilesSelected={handleUploadOriginal}
              loading={uploadingOriginal}
              accept=".docx,.pptx,.txt,.md,.pdf"
              multiple={false}
            />
          )}
        </div>

        {/* Step 2: Supplementary materials */}
        {docInfo && (
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">
              2. 추가 자료 (선택)
            </label>
            <p className="text-xs text-[#787774] mb-3">
              업데이트에 참고할 추가 자료를 올리거나 텍스트를 붙여넣으세요.
            </p>
            <FilePicker
              onFilesSelected={handleUploadSupplementary}
              loading={uploadingSup}
            />
            {supFileNames.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 items-center">
                {supFileNames.map((name, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2.5 py-1 bg-[#E8F3FC] text-[#2383E2] text-xs rounded-lg"
                  >
                    📄 {name}
                  </span>
                ))}
                <button
                  onClick={() => setSupFileNames([])}
                  className="text-xs text-[#EB5757] hover:underline ml-1"
                >
                  전체 삭제
                </button>
              </div>
            )}
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="또는 여기에 추가 자료 텍스트를 붙여넣으세요..."
              rows={3}
              className="w-full mt-3 px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
            />
          </div>
        )}

        {/* Step 3: Instruction & Mode */}
        {docInfo && (
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">
              3. 업데이트 지시사항
            </label>

            {/* Mode toggle */}
            <div className="flex gap-2 mb-3">
              {MODE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setMode(opt.value)}
                  className={`flex-1 px-3 py-2 text-xs rounded-lg border transition-colors text-left ${
                    mode === opt.value
                      ? 'border-[#2383E2] bg-[#E8F3FC] text-[#2383E2]'
                      : 'border-[#E9E9E7] hover:bg-[#F7F6F3] text-[#37352F]'
                  }`}
                >
                  <div className="font-medium">{opt.label}</div>
                  <div
                    className={`mt-0.5 ${
                      mode === opt.value ? 'text-[#2383E2]/70' : 'text-[#787774]'
                    }`}
                  >
                    {opt.desc}
                  </div>
                </button>
              ))}
            </div>

            {/* Presets */}
            <div className="flex flex-wrap gap-2 mb-3">
              {PRESETS.map((p, i) => (
                <button
                  key={i}
                  onClick={() => handlePresetChange(i)}
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
              placeholder="예: 2024년 실적 데이터를 반영하여 수치를 업데이트해주세요..."
              rows={3}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
            />
          </div>
        )}

        {/* Generate button */}
        {docInfo && (
          <button
            onClick={handleRun}
            disabled={!canRun}
            className={`w-full py-3 font-semibold rounded-xl transition-colors text-sm ${
              canRun
                ? 'bg-[#2383E2] text-white hover:bg-[#1b6ec2]'
                : 'bg-[#E9E9E7] text-[#9B9A97] cursor-not-allowed'
            }`}
          >
            {generating ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                문서 업데이트 중...
              </span>
            ) : (
              '🚀 업데이트 시작'
            )}
          </button>
        )}
      </div>
    </div>
  );
}
