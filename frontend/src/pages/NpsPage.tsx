import { useState } from 'react';

interface NpsRow {
  자료생성년월: string;
  사업장명: string;
  가입자수: number;
  당월고지금액: number;
  신규취득자수: number;
  상실가입자수: number;
  사업장업종코드명: string;
  사업장도로명상세주소: string;
  사업장형태구분코드: number;
  [key: string]: any;
}

const fmt = (n: number | null) => (n != null ? n.toLocaleString('ko-KR') : '-');
const fmtWon = (n: number) => {
  if (n >= 1e8) return (n / 1e8).toFixed(1) + '억';
  if (n >= 1e4) return Math.round(n / 1e4).toLocaleString() + '만';
  return fmt(n);
};

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: CURRENT_YEAR - 2014 }, (_, i) => CURRENT_YEAR - i);

export default function NpsPage() {
  const [name, setName] = useState('');
  const [year, setYear] = useState(CURRENT_YEAR);
  const [month, setMonth] = useState(0);
  const [results, setResults] = useState<NpsRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState('');
  const [page, setPage] = useState(1);
  const [perPage] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [sortKey, setSortKey] = useState('');
  const [sortAsc, setSortAsc] = useState(true);

  const doSearch = async (pg = 1) => {
    if (!name && !year) return;
    setLoading(true);
    setPage(pg);
    const t0 = performance.now();

    const params = new URLSearchParams();
    if (name) params.set('name', name);
    if (year) params.set('year', String(year));
    if (month) params.set('month', String(month));
    params.set('page', String(pg));
    params.set('perPage', String(perPage));

    try {
      const res = await fetch(`/api/nps/search?${params}`);
      const json = await res.json();
      if (json.error) {
        setResults([]);
        setTotal(0);
      } else {
        setResults(json.data || []);
        setTotal(json.total || 0);
        setTotalPages(Math.ceil((json.total || 0) / perPage));
      }
    } catch {
      setResults([]);
    }
    setElapsed(((performance.now() - t0) / 1000).toFixed(2));
    setLoading(false);
  };

  const handleSort = (key: string) => {
    const asc = sortKey === key ? !sortAsc : true;
    setSortKey(key);
    setSortAsc(asc);
    const sorted = [...results].sort((a, b) => {
      const va = a[key], vb = b[key];
      if (typeof va === 'number' && typeof vb === 'number') return asc ? va - vb : vb - va;
      return asc
        ? String(va || '').localeCompare(String(vb || ''), 'ko')
        : String(vb || '').localeCompare(String(va || ''), 'ko');
    });
    setResults(sorted);
  };

  const exportCsv = () => {
    const header = '자료생성년월,사업장명,가입자수,당월고지금액,신규취득,상실,업종,주소\n';
    const rows = results.map((r) =>
      `"${r.자료생성년월}","${r.사업장명}",${r.가입자수},${r.당월고지금액},${r.신규취득자수},${r.상실가입자수},"${r.사업장업종코드명 || ''}","${r.사업장도로명상세주소 || ''}"`
    ).join('\n');
    const blob = new Blob(['\uFEFF' + header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nps_${name || 'all'}_${year}${month ? '-' + String(month).padStart(2, '0') : ''}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalSubs = results.reduce((s, r) => s + (r.가입자수 || 0), 0);
  const totalAmt = results.reduce((s, r) => s + (r.당월고지금액 || 0), 0);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">🏢 국민연금 사업장 조회</h1>
      <p className="text-sm text-[#787774] mb-6">
        국민연금 가입 사업장 내역을 연도/월/사업장명으로 조회합니다.
        <span className="ml-2 text-xs text-[#b0b0b0]">출처: data.go.kr OpenAPI</span>
      </p>

      {/* 검색 폼 */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <div className="flex gap-3 items-end flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-[#787774] mb-1">사업장명</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && doSearch()}
              placeholder="삼성전자, 카카오, 네이버 ..."
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-[#787774] mb-1">연도</label>
            <select value={year} onChange={(e) => setYear(+e.target.value)}
              className="px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]">
              {YEARS.map((y) => <option key={y} value={y}>{y}년</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-[#787774] mb-1">월</label>
            <select value={month} onChange={(e) => setMonth(+e.target.value)}
              className="px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]">
              <option value={0}>전체</option>
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={i + 1}>{i + 1}월</option>
              ))}
            </select>
          </div>
          <button onClick={() => doSearch()} disabled={loading || (!name && !year)}
            className="px-6 py-2 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors">
            {loading ? '조회 중...' : '🔍 조회'}
          </button>
        </div>
      </div>

      {/* 상태 & 요약 */}
      {results.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm text-[#787774]">
              총 <span className="font-semibold text-[#37352F]">{fmt(total)}</span>건
              {results.length < total && ` (${fmt(results.length)}건 로드)`}
              <span className="ml-2 text-xs text-[#b0b0b0]">{elapsed}s</span>
            </div>
            <button onClick={exportCsv}
              className="px-3 py-1 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] transition-colors">
              📥 CSV 내보내기
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-white border border-[#E9E9E7] rounded-xl p-3">
              <div className="text-xs text-[#787774] mb-1">조회 건수</div>
              <div className="text-lg font-bold text-[#2383E2]">{fmt(total)}</div>
            </div>
            <div className="bg-white border border-[#E9E9E7] rounded-xl p-3">
              <div className="text-xs text-[#787774] mb-1">총 가입자수</div>
              <div className="text-lg font-bold text-[#27AE60]">{fmt(totalSubs)}명</div>
            </div>
            <div className="bg-white border border-[#E9E9E7] rounded-xl p-3">
              <div className="text-xs text-[#787774] mb-1">총 당월고지금액</div>
              <div className="text-lg font-bold text-[#E2B93B]">{fmtWon(totalAmt)}원</div>
            </div>
          </div>
        </>
      )}

      {/* 결과 테이블 */}
      {results.length > 0 && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl overflow-hidden">
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#F7F6F3] sticky top-0">
                <tr>
                  {[
                    { key: '자료생성년월', label: '년월', align: 'left' },
                    { key: '사업장명', label: '사업장명', align: 'left' },
                    { key: '가입자수', label: '가입자수', align: 'right' },
                    { key: '당월고지금액', label: '당월고지금액', align: 'right' },
                    { key: '신규취득자수', label: '신규', align: 'right' },
                    { key: '상실가입자수', label: '상실', align: 'right' },
                    { key: '사업장업종코드명', label: '업종', align: 'left' },
                    { key: '사업장도로명상세주소', label: '주소', align: 'left' },
                  ].map((col) => (
                    <th key={col.key} onClick={() => handleSort(col.key)}
                      className={`px-3 py-2 text-[#787774] font-medium cursor-pointer hover:text-[#37352F] transition-colors whitespace-nowrap ${col.align === 'right' ? 'text-right' : 'text-left'}`}>
                      {col.label}
                      {sortKey === col.key && <span className="ml-1">{sortAsc ? '▲' : '▼'}</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className="border-t border-[#E9E9E7] hover:bg-[#FAFAF9]">
                    <td className="px-3 py-2 text-[#787774] font-mono text-xs">{r.자료생성년월}</td>
                    <td className="px-3 py-2 text-[#37352F] font-medium truncate max-w-[220px]" title={r.사업장명}>{r.사업장명}</td>
                    <td className="px-3 py-2 text-right font-mono">{fmt(r.가입자수)}</td>
                    <td className="px-3 py-2 text-right font-mono">{fmt(r.당월고지금액)}</td>
                    <td className="px-3 py-2 text-right font-mono text-[#27AE60]">{fmt(r.신규취득자수)}</td>
                    <td className="px-3 py-2 text-right font-mono text-[#EB5757]">{fmt(r.상실가입자수)}</td>
                    <td className="px-3 py-2 text-[#787774] truncate max-w-[180px]" title={r.사업장업종코드명 || ''}>{(r.사업장업종코드명 || '').slice(0, 18)}</td>
                    <td className="px-3 py-2 text-[#787774] truncate max-w-[200px]" title={r.사업장도로명상세주소 || ''}>{(r.사업장도로명상세주소 || '').slice(0, 22)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 페이지네이션 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 px-4 py-3 border-t border-[#E9E9E7]">
              <button onClick={() => doSearch(page - 1)} disabled={page <= 1}
                className="px-3 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3] disabled:opacity-30">
                &lt; 이전
              </button>
              <span className="text-xs text-[#787774]">{page} / {totalPages}</span>
              <button onClick={() => doSearch(page + 1)} disabled={page >= totalPages}
                className="px-3 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3] disabled:opacity-30">
                다음 &gt;
              </button>
            </div>
          )}
        </div>
      )}

      {/* 빈 상태 */}
      {!loading && results.length === 0 && elapsed && (
        <div className="text-center py-12 text-[#787774]">
          <div className="text-3xl mb-3 opacity-30">🔍</div>
          <p className="text-sm">검색 결과가 없습니다</p>
        </div>
      )}
    </div>
  );
}
