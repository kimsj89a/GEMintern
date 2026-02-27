import { useEffect, useState } from 'react';
import { api } from '../api/client';

export default function AdminPage() {
  const [codes, setCodes] = useState<any[]>([]);
  const [usage, setUsage] = useState<any[]>([]);
  const [newCodes, setNewCodes] = useState<string[]>([]);
  const [codeCount, setCodeCount] = useState(1);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'codes' | 'usage'>('codes');

  const loadData = async () => {
    try {
      const [c, u] = await Promise.all([api.listInviteCodes(), api.getUsageStats()]);
      setCodes(c);
      setUsage(u);
    } catch { /* ignore */ }
  };

  useEffect(() => { loadData(); }, []);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await api.createInviteCodes(codeCount);
      setNewCodes(result.codes);
      loadData();
    } catch { /* ignore */ }
    setLoading(false);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">🛡️ 관리자</h1>
      <p className="text-sm text-[#787774] mb-6">초대코드 관리 및 사용량 모니터링</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-[#F7F6F3] rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab('codes')}
          className={`px-4 py-2 text-sm rounded-md transition-all ${
            tab === 'codes' ? 'bg-white shadow-sm text-[#37352F] font-medium' : 'text-[#787774]'
          }`}
        >
          초대코드
        </button>
        <button
          onClick={() => setTab('usage')}
          className={`px-4 py-2 text-sm rounded-md transition-all ${
            tab === 'usage' ? 'bg-white shadow-sm text-[#37352F] font-medium' : 'text-[#787774]'
          }`}
        >
          사용량
        </button>
      </div>

      {tab === 'codes' && (
        <div>
          {/* Generate */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-6 mb-4">
            <h2 className="text-sm font-semibold text-[#37352F] mb-3">초대코드 생성</h2>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={20}
                value={codeCount}
                onChange={(e) => setCodeCount(Number(e.target.value))}
                className="w-20 px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]"
              />
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="px-4 py-2 bg-[#2383E2] text-white text-sm rounded-lg hover:bg-[#1b6ec2] disabled:opacity-50"
              >
                {loading ? '...' : '생성'}
              </button>
            </div>

            {newCodes.length > 0 && (
              <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="text-xs text-green-700 font-medium mb-2">생성된 코드 (클릭하여 복사)</div>
                <div className="flex flex-wrap gap-2">
                  {newCodes.map((c) => (
                    <button
                      key={c}
                      onClick={() => copyToClipboard(c)}
                      className="px-2 py-1 bg-white border border-green-300 rounded text-xs font-mono text-green-800 hover:bg-green-100 transition-colors"
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Code list */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E9E9E7] bg-[#F7F6F3]">
                  <th className="text-left px-4 py-2.5 text-[#787774] font-medium">코드</th>
                  <th className="text-left px-4 py-2.5 text-[#787774] font-medium">생성자</th>
                  <th className="text-left px-4 py-2.5 text-[#787774] font-medium">상태</th>
                  <th className="text-left px-4 py-2.5 text-[#787774] font-medium">생성일</th>
                </tr>
              </thead>
              <tbody>
                {codes.map((c) => (
                  <tr key={c.id} className="border-b border-[#E9E9E7] last:border-b-0">
                    <td className="px-4 py-2.5 font-mono text-xs">{c.code}</td>
                    <td className="px-4 py-2.5 text-[#787774]">{c.created_by || '-'}</td>
                    <td className="px-4 py-2.5">
                      {c.used_by ? (
                        <span className="text-xs text-[#787774]">
                          사용됨 ({c.used_by})
                        </span>
                      ) : (
                        <span className="text-xs text-emerald-600 font-medium">미사용</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-[#787774]">
                      {c.created_at?.slice(0, 16).replace('T', ' ')}
                    </td>
                  </tr>
                ))}
                {codes.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-[#787774]">초대코드가 없습니다.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'usage' && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E9E9E7] bg-[#F7F6F3]">
                <th className="text-left px-4 py-2.5 text-[#787774] font-medium">사용자</th>
                <th className="text-left px-4 py-2.5 text-[#787774] font-medium">엔드포인트</th>
                <th className="text-left px-4 py-2.5 text-[#787774] font-medium">모델</th>
                <th className="text-right px-4 py-2.5 text-[#787774] font-medium">호출수</th>
                <th className="text-left px-4 py-2.5 text-[#787774] font-medium">최근 사용</th>
              </tr>
            </thead>
            <tbody>
              {usage.map((u, i) => (
                <tr key={i} className="border-b border-[#E9E9E7] last:border-b-0">
                  <td className="px-4 py-2.5 font-medium">{u.username}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{u.endpoint}</td>
                  <td className="px-4 py-2.5 text-xs text-[#787774]">{u.model || '-'}</td>
                  <td className="px-4 py-2.5 text-right font-medium">{u.count}</td>
                  <td className="px-4 py-2.5 text-xs text-[#787774]">
                    {u.last_use?.slice(0, 16).replace('T', ' ')}
                  </td>
                </tr>
              ))}
              {usage.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-[#787774]">사용 기록이 없습니다.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
