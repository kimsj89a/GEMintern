import { useRef, useState } from 'react';

export default function PdfUnlockPage() {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    setFile(selected);
    setMessage(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === 'application/pdf') {
      setFile(dropped);
      setMessage(null);
    }
  };

  const handleUnlock = async () => {
    if (!file || !password) return;
    setLoading(true);
    setMessage(null);

    try {
      const { api } = await import('../api/client');
      const result = await api.unlockPdf(file, password);
      setMessage({ type: 'success', text: `${result.filename} 다운로드 완료` });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || '잠금 해제 실패' });
    }
    setLoading(false);
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">PDF 잠금 해제</h1>
      <p className="text-sm text-[#787774] mb-6">
        비밀번호로 보호된 PDF의 잠금을 해제합니다.
      </p>

      {/* File picker */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <label className="block text-sm font-medium text-[#37352F] mb-2">PDF 파일</label>
        <div
          className="border-2 border-dashed border-[#E9E9E7] rounded-xl p-6 text-center cursor-pointer hover:border-[#2383E2] hover:bg-[#FAFAF9] transition-colors"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            onChange={handleFile}
            className="hidden"
          />
          <div className="text-3xl mb-2">📎</div>
          <div className="text-sm text-[#37352F]">
            {file ? file.name : 'PDF 파일을 선택하거나 드래그하세요'}
          </div>
        </div>
      </div>

      {/* Password */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <label className="block text-sm font-medium text-[#37352F] mb-2">비밀번호</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="PDF 비밀번호를 입력하세요"
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#2383E2] focus:border-transparent"
          onKeyDown={(e) => e.key === 'Enter' && handleUnlock()}
        />
      </div>

      {/* Action */}
      <button
        onClick={handleUnlock}
        disabled={!file || !password || loading}
        className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4"
      >
        {loading ? '잠금 해제 중...' : '잠금 해제 및 다운로드'}
      </button>

      {/* Message */}
      {message && (
        <div
          className={`p-3 rounded-xl text-sm ${
            message.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}
