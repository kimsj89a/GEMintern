import { useRef, useState } from 'react';
import { api } from '../api/client';
import MarkdownViewer from '../components/MarkdownViewer';
import { generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';

export default function PptToolsPage() {
  const { currentProject } = useAppStore();
  const [tab, setTab] = useState<'generate' | 'update'>('generate');

  // Generate tab
  const [files, setFiles] = useState<File[]>([]);
  const [context, setContext] = useState('');
  const [slideResult, setSlideResult] = useState('');
  const [generating, setGenerating] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const cancelGenRef = useRef(false);

  // Update tab
  const [pptxFile, setPptxFile] = useState<File | null>(null);
  const [updateStatus, setUpdateStatus] = useState('');
  const [updating, setUpdating] = useState(false);
  const updateAbortRef = useRef<AbortController | null>(null);

  const handleGenerate = async () => {
    if (files.length === 0) return;
    setGenerating(true);
    setSlideResult('');
    cancelGenRef.current = false;

    try {
      const formData = new FormData();
      files.forEach((f) => formData.append('files', f));
      formData.append('context', context);

      const { task_id } = await api.startAnalysis({
        task_type: 'slide_json',
        kwargs: { file_context: context },
      });

      const check = async () => {
        if (cancelGenRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          setSlideResult(typeof status.result === 'string' ? status.result : JSON.stringify(status.result, null, 2));
          setGenerating(false);
        } else if (status.status === 'error') {
          setSlideResult(`오류: ${status.error}`);
          setGenerating(false);
        } else {
          setTimeout(check, 1000);
        }
      };
      check();
    } catch (err: any) {
      setSlideResult(`오류: ${err.message}`);
      setGenerating(false);
    }
  };

  const handleStopGenerate = () => {
    cancelGenRef.current = true;
    setGenerating(false);
  };

  const handleDownloadPptx = async () => {
    try {
      const res = await fetch('/api/create-pptx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slide_json: slideResult }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = generateFilename('발표자료', 'pptx', currentProject); a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`PPTX 생성 실패: ${err.message}`);
    }
  };

  const handleUpdate = async () => {
    if (!pptxFile) return;
    setUpdating(true);
    setUpdateStatus('');
    const controller = new AbortController();
    updateAbortRef.current = controller;
    try {
      const formData = new FormData();
      formData.append('file', pptxFile);

      const res = await fetch('/api/update-pptx-history', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = generateFilename('PPT업데이트', 'pptx', currentProject); a.click();
        URL.revokeObjectURL(url);
        setUpdateStatus('업데이트 완료! 파일이 다운로드됩니다.');
      } else {
        const data = await res.json();
        setUpdateStatus(`오류: ${data.error || '업데이트 실패'}`);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') setUpdateStatus(`오류: ${err.message}`);
    }
    setUpdating(false);
  };

  const handleStopUpdate = () => {
    updateAbortRef.current?.abort();
    setUpdating(false);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">📢 발표자료 (PPT)</h1>
      <p className="text-sm text-[#787774] mb-6">문서 기반 PPT 생성 및 투자이력 업데이트</p>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab('generate')}
          className={`px-4 py-2 text-sm rounded-lg ${tab === 'generate' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          📊 PPT 생성
        </button>
        <button onClick={() => setTab('update')}
          className={`px-4 py-2 text-sm rounded-lg ${tab === 'update' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}>
          🔄 투자이력 업데이트
        </button>
      </div>

      {tab === 'generate' && (
        <div>
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">참조 문서</label>
            <div
              className="border-2 border-dashed border-[#E9E9E7] rounded-xl p-6 text-center cursor-pointer hover:border-[#2383E2] transition-colors"
              onClick={() => fileRef.current?.click()}
            >
              <input ref={fileRef} type="file" multiple onChange={(e) => setFiles(Array.from(e.target.files || []))} className="hidden" />
              <div className="text-2xl mb-1">📎</div>
              <div className="text-sm text-[#37352F]">
                {files.length > 0 ? `${files.length}개 파일 선택됨` : '문서 파일을 선택하세요'}
              </div>
            </div>
          </div>

          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">발표 범위/지시사항</label>
            <textarea value={context} onChange={(e) => setContext(e.target.value)}
              placeholder="PPT에 포함할 범위나 특별 지시사항을 입력하세요..."
              rows={3}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none" />
          </div>

          {generating ? (
            <div className="flex gap-2 mb-4">
              <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
                생성 중...
              </div>
              <button onClick={handleStopGenerate}
                className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
                중지
              </button>
            </div>
          ) : (
            <button onClick={handleGenerate} disabled={files.length === 0}
              className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
              📊 PPT 생성
            </button>
          )}

          {slideResult && (
            <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-[#37352F]">슬라이드 구조</div>
                <button onClick={handleDownloadPptx} className="px-3 py-1.5 text-xs bg-[#2383E2] text-white rounded-lg hover:bg-[#1b6ec2]">
                  📥 PPTX 다운로드
                </button>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <MarkdownViewer content={slideResult} />
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'update' && (
        <div>
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            <label className="block text-sm font-medium text-[#37352F] mb-2">PPTX 파일</label>
            <label className="inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3]">
              📂 PPTX 파일 선택
              <input type="file" accept=".pptx" onChange={(e) => setPptxFile(e.target.files?.[0] || null)} className="hidden" />
            </label>
            {pptxFile && <span className="ml-2 text-xs text-[#787774]">{pptxFile.name}</span>}
          </div>

          {updating ? (
            <div className="flex gap-2 mb-4">
              <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
                업데이트 중...
              </div>
              <button onClick={handleStopUpdate}
                className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
                중지
              </button>
            </div>
          ) : (
            <button onClick={handleUpdate} disabled={!pptxFile}
              className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
              🔄 투자이력 업데이트
            </button>
          )}

          {updateStatus && (
            <div className={`px-4 py-3 rounded-lg text-sm ${updateStatus.startsWith('오류') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
              {updateStatus}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
