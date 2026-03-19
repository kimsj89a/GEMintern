import { useState, useMemo } from 'react';
import { api } from '../api/client';

interface ScannedFile {
  path: string;
  name: string;
  size: number;
  ext: string;
  relative_path: string;
}

interface FolderScanModalProps {
  projectName: string;
  onClose: () => void;
  onComplete: () => void;
}

const EXTENSION_GROUPS: { label: string; exts: string[] }[] = [
  { label: '문서', exts: ['.pdf', '.docx', '.doc', '.txt', '.md'] },
  { label: '스프레드시트', exts: ['.xlsx', '.xls', '.csv'] },
  { label: '프레젠테이션', exts: ['.pptx', '.ppt'] },
  { label: '웹/데이터', exts: ['.json', '.xml', '.html', '.htm'] },
  { label: '이미지', exts: ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'] },
];

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type Step = 'scan' | 'preview' | 'ingesting' | 'done';

export default function FolderScanModal({ projectName, onClose, onComplete }: FolderScanModalProps) {
  const [step, setStep] = useState<Step>('scan');
  const [folderPath, setFolderPath] = useState('');
  const [recursive, setRecursive] = useState(true);
  const [selectedExts, setSelectedExts] = useState<string[]>([]);
  const [scanning, setScanning] = useState(false);
  const [files, setFiles] = useState<ScannedFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [preserveStructure, setPreserveStructure] = useState(true);
  const [error, setError] = useState('');
  const [ingestResult, setIngestResult] = useState<{
    indexed: string[]; skipped: string[]; errors: any[];
  } | null>(null);
  const [ingestProgress, setIngestProgress] = useState('');

  // Build a simple tree structure from relative_path for display
  const fileTree = useMemo(() => {
    const tree: Record<string, ScannedFile[]> = {};
    for (const f of files) {
      const dir = f.relative_path.includes('/')
        ? f.relative_path.substring(0, f.relative_path.lastIndexOf('/'))
        : '(root)';
      if (!tree[dir]) tree[dir] = [];
      tree[dir].push(f);
    }
    return tree;
  }, [files]);

  const selectedSize = useMemo(() => {
    return files.filter(f => selectedFiles.has(f.path)).reduce((s, f) => s + f.size, 0);
  }, [files, selectedFiles]);

  const handleScan = async () => {
    if (!folderPath.trim()) { setError('폴더 경로를 입력하세요.'); return; }
    setScanning(true);
    setError('');
    try {
      const result = await api.scanFolderPreview({
        folder_path: folderPath.trim(),
        recursive,
        file_extensions: selectedExts,
      });
      setFiles(result.files);
      setSelectedFiles(new Set(result.files.map(f => f.path)));
      setStep('preview');
    } catch (err: any) {
      setError(err.message || '스캔 실패');
    } finally {
      setScanning(false);
    }
  };

  const handleSelectAll = () => setSelectedFiles(new Set(files.map(f => f.path)));
  const handleSelectNone = () => setSelectedFiles(new Set());

  const toggleFile = (path: string) => {
    setSelectedFiles(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const toggleFolder = (dir: string) => {
    const folderFiles = fileTree[dir] || [];
    const allSelected = folderFiles.every(f => selectedFiles.has(f.path));
    setSelectedFiles(prev => {
      const next = new Set(prev);
      for (const f of folderFiles) {
        if (allSelected) next.delete(f.path);
        else next.add(f.path);
      }
      return next;
    });
  };

  const handleIngest = async () => {
    if (selectedFiles.size === 0) { setError('파일을 선택하세요.'); return; }
    setStep('ingesting');
    setError('');
    setIngestProgress(`${selectedFiles.size}개 파일 분석 중...`);
    try {
      const result = await api.ingestScannedFiles(projectName, {
        folder_path: folderPath.trim(),
        selected_files: Array.from(selectedFiles),
        preserve_structure: preserveStructure,
      });
      setIngestResult(result);
      setStep('done');
      onComplete();
    } catch (err: any) {
      setError(err.message || '인덱싱 실패');
      setStep('preview');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-2xl shadow-2xl w-[680px] max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E9E9E7]">
          <h2 className="text-[15px] font-semibold text-[#37352F]">
            폴더 스캔
          </h2>
          <button onClick={onClose}
            className="text-[#9B9A97] hover:text-[#37352F] text-lg transition-colors">&times;</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {error && (
            <div className="px-3 py-2 rounded-lg text-[13px] bg-red-50 text-red-600 border border-red-100">
              {error}
              <button className="ml-2 text-red-400 hover:text-red-600 text-xs" onClick={() => setError('')}>닫기</button>
            </div>
          )}

          {/* Step 1: Scan config */}
          {(step === 'scan' || step === 'preview') && (
            <div className="space-y-3">
              <div>
                <label className="block text-[12px] font-medium text-[#787774] mb-1">폴더 경로</label>
                <div className="flex gap-2">
                  <input
                    value={folderPath}
                    onChange={(e) => setFolderPath(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && step === 'scan' && handleScan()}
                    placeholder="C:\Users\...\Documents"
                    className="flex-1 px-3 py-2 border border-[#E9E9E7] rounded-lg text-[13px] bg-white focus:outline-none focus:border-[#2383E2] focus:ring-1 focus:ring-[#2383E2]/20 transition-shadow"
                    disabled={step !== 'scan'}
                  />
                  <button onClick={step === 'scan' ? handleScan : () => { setStep('scan'); setFiles([]); }}
                    disabled={scanning}
                    className="px-4 py-2 bg-[#2383E2] text-white text-[13px] font-medium rounded-lg hover:bg-[#1b6ec2] disabled:opacity-40 transition-colors whitespace-nowrap">
                    {scanning ? '스캔 중...' : step === 'scan' ? '스캔' : '다시 스캔'}
                  </button>
                </div>
              </div>

              {step === 'scan' && (
                <>
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-1.5 text-[12px] text-[#37352F] cursor-pointer">
                      <input type="checkbox" checked={recursive}
                        onChange={(e) => setRecursive(e.target.checked)}
                        className="rounded border-[#D3D3D0] text-[#2383E2] focus:ring-[#2383E2]/30" />
                      하위 폴더 포함
                    </label>
                  </div>
                  <div>
                    <label className="block text-[12px] font-medium text-[#787774] mb-1.5">파일 유형 필터 (미선택 시 전체)</label>
                    <div className="flex flex-wrap gap-2">
                      {EXTENSION_GROUPS.map(g => {
                        const active = g.exts.some(e => selectedExts.includes(e));
                        return (
                          <button key={g.label} onClick={() => {
                            setSelectedExts(prev => {
                              if (active) return prev.filter(e => !g.exts.includes(e));
                              return [...prev, ...g.exts.filter(e => !prev.includes(e))];
                            });
                          }}
                            className={`px-2.5 py-1 text-[11px] rounded-full border transition-colors ${active
                              ? 'bg-[#2383E2]/10 text-[#2383E2] border-[#2383E2]/30'
                              : 'bg-[#FAFAF9] text-[#787774] border-[#E9E9E7] hover:bg-[#F0F0EE]'
                            }`}>
                            {g.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 2: File preview */}
          {step === 'preview' && files.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-[13px] text-[#37352F]">
                  <span className="font-medium">{files.length}개 파일</span>
                  <span className="text-[#9B9A97] ml-2">
                    (선택: {selectedFiles.size}개, {formatSize(selectedSize)})
                  </span>
                </div>
                <div className="flex gap-1.5">
                  <button onClick={handleSelectAll}
                    className="px-2 py-1 text-[11px] text-[#787774] hover:text-[#2383E2] hover:bg-[#2383E2]/5 rounded transition-colors">
                    전체 선택
                  </button>
                  <button onClick={handleSelectNone}
                    className="px-2 py-1 text-[11px] text-[#787774] hover:text-red-500 hover:bg-red-50/50 rounded transition-colors">
                    전체 해제
                  </button>
                </div>
              </div>

              <div className="border border-[#E9E9E7] rounded-xl max-h-[320px] overflow-y-auto">
                {Object.entries(fileTree).sort(([a], [b]) => a.localeCompare(b)).map(([dir, dirFiles]) => {
                  const allSelected = dirFiles.every(f => selectedFiles.has(f.path));
                  const someSelected = dirFiles.some(f => selectedFiles.has(f.path));
                  return (
                    <div key={dir}>
                      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#FAFAF9] border-b border-[#F0F0EE] sticky top-0">
                        <input type="checkbox"
                          checked={allSelected}
                          ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                          onChange={() => toggleFolder(dir)}
                          className="rounded border-[#D3D3D0] text-[#2383E2] focus:ring-[#2383E2]/30" />
                        <span className="text-[11px] font-medium text-[#787774]">
                          {dir === '(root)' ? '(root)' : dir}
                        </span>
                        <span className="text-[10px] text-[#B4B4B0]">{dirFiles.length}개</span>
                      </div>
                      {dirFiles.map(f => (
                        <label key={f.path}
                          className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#F7F6F3] cursor-pointer border-b border-[#F8F8F7] last:border-0">
                          <input type="checkbox"
                            checked={selectedFiles.has(f.path)}
                            onChange={() => toggleFile(f.path)}
                            className="rounded border-[#D3D3D0] text-[#2383E2] focus:ring-[#2383E2]/30 shrink-0" />
                          <span className="text-[12px] text-[#37352F] truncate flex-1">{f.name}</span>
                          <span className="text-[10px] text-[#B4B4B0] tabular-nums shrink-0">{formatSize(f.size)}</span>
                          <span className="text-[10px] text-[#B4B4B0] shrink-0 w-10 text-right">{f.ext}</span>
                        </label>
                      ))}
                    </div>
                  );
                })}
              </div>

              <label className="flex items-center gap-1.5 text-[12px] text-[#37352F] cursor-pointer">
                <input type="checkbox" checked={preserveStructure}
                  onChange={(e) => setPreserveStructure(e.target.checked)}
                  className="rounded border-[#D3D3D0] text-[#2383E2] focus:ring-[#2383E2]/30" />
                폴더 구조 유지
              </label>
            </div>
          )}

          {step === 'preview' && files.length === 0 && (
            <div className="text-center py-8 text-[13px] text-[#9B9A97]">
              지원되는 파일이 없습니다.
            </div>
          )}

          {/* Step 3: Ingesting */}
          {step === 'ingesting' && (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-2 border-[#2383E2] border-t-transparent rounded-full animate-spin mb-3" />
              <div className="text-[13px] text-[#37352F]">{ingestProgress}</div>
              <div className="text-[11px] text-[#9B9A97] mt-1">파일 파싱 및 인덱싱 중입니다. 잠시 기다려주세요...</div>
            </div>
          )}

          {/* Step 4: Results */}
          {step === 'done' && ingestResult && (
            <div className="space-y-3">
              <div className="text-center py-4">
                <div className="text-2xl mb-2">
                  {ingestResult.errors.length === 0 ? '\u2705' : '\u26A0\uFE0F'}
                </div>
                <div className="text-[14px] font-medium text-[#37352F]">분석 완료</div>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="px-3 py-2.5 bg-emerald-50 rounded-xl border border-emerald-100">
                  <div className="text-[18px] font-semibold text-emerald-600 tabular-nums">{ingestResult.indexed.length}</div>
                  <div className="text-[11px] text-emerald-500">인덱싱 성공</div>
                </div>
                <div className="px-3 py-2.5 bg-amber-50 rounded-xl border border-amber-100">
                  <div className="text-[18px] font-semibold text-amber-600 tabular-nums">{ingestResult.skipped.length}</div>
                  <div className="text-[11px] text-amber-500">건너뜀</div>
                </div>
                <div className="px-3 py-2.5 bg-red-50 rounded-xl border border-red-100">
                  <div className="text-[18px] font-semibold text-red-600 tabular-nums">{ingestResult.errors.length}</div>
                  <div className="text-[11px] text-red-500">오류</div>
                </div>
              </div>
              {ingestResult.indexed.length > 0 && (
                <details className="text-[12px]">
                  <summary className="cursor-pointer text-[#787774] hover:text-[#37352F]">인덱싱된 파일 목록</summary>
                  <div className="mt-1 pl-3 text-[#9B9A97] space-y-0.5">
                    {ingestResult.indexed.map(f => <div key={f}>{f}</div>)}
                  </div>
                </details>
              )}
              {ingestResult.errors.length > 0 && (
                <details className="text-[12px]">
                  <summary className="cursor-pointer text-red-500">오류 상세</summary>
                  <div className="mt-1 pl-3 text-red-400 space-y-0.5">
                    {ingestResult.errors.map((e, i) => (
                      <div key={i}>{e.file || e.folder}: {e.error}</div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-3 border-t border-[#E9E9E7] bg-[#FAFAF9]">
          {step === 'preview' && (
            <button onClick={handleIngest}
              disabled={selectedFiles.size === 0}
              className="px-4 py-2 bg-[#2383E2] text-white text-[13px] font-medium rounded-lg hover:bg-[#1b6ec2] disabled:opacity-40 transition-colors">
              선택한 파일 분석 ({selectedFiles.size}개)
            </button>
          )}
          <button onClick={onClose}
            className="px-4 py-2 text-[13px] text-[#787774] border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] transition-colors">
            {step === 'done' ? '닫기' : '취소'}
          </button>
        </div>
      </div>
    </div>
  );
}
