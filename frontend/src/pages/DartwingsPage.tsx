import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../stores/authStore';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';

// ── API helpers ──
const BASE = '/api/dartwings';

function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function dwFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: getAuthHeaders() });
  if (res.status === 401) { useAuthStore.getState().logout(); throw new Error('Unauthorized'); }
  if (!res.ok) { const t = await res.text(); throw new Error(`API ${res.status}: ${t}`); }
  return res.json();
}

// ── Formatters ──
function formatKRW(v: number): string {
  if (!v) return '-';
  const abs = Math.abs(v);
  if (abs >= 1e12) return `${(v / 1e12).toFixed(1)}조`;
  if (abs >= 1e8) return `${(v / 1e8).toFixed(0)}억`;
  if (abs >= 1e4) return `${(v / 1e4).toFixed(0)}만`;
  return v.toLocaleString();
}

function formatPrice(v: number): string {
  return v ? v.toLocaleString() + '원' : '-';
}

function formatPercent(v: number): string {
  return v ? v.toFixed(2) + '%' : '-';
}

function formatDate(raw: string): string {
  if (!raw || raw.length !== 8) return raw || '-';
  return `${raw.slice(0, 4)}.${raw.slice(4, 6)}.${raw.slice(6, 8)}`;
}

// ── Colors ──
const COLORS = {
  accent: '#3b82f6', green: '#22c55e', red: '#ef4444', amber: '#f59e0b',
  slate: '#64748b', purple: '#8b5cf6', cyan: '#06b6d4', pink: '#ec4899',
};
const PIE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

// ── SearchBar ──
function SearchBar({ onSelect }: { onSelect: (code: string, name: string) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setShow(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const doSearch = useCallback((q: string) => {
    if (q.length < 1) { setResults([]); return; }
    setLoading(true);
    dwFetch<any[]>(`/search?q=${encodeURIComponent(q)}&limit=10`)
      .then(r => { setResults(r); setShow(true); })
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, []);

  const onChange = (v: string) => {
    setQuery(v);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => doSearch(v), 300);
  };

  return (
    <div ref={ref} className="relative max-w-lg mx-auto">
      <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white border border-slate-200 focus-within:border-blue-500/60 transition-colors">
        <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          className="flex-1 bg-transparent text-slate-900 placeholder-slate-400 outline-none text-sm"
          placeholder="종목명 또는 종목코드 검색..."
          value={query}
          onChange={e => onChange(e.target.value)}
          onFocus={() => results.length > 0 && setShow(true)}
        />
        {loading && <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />}
        {query && !loading && (
          <button onClick={() => { setQuery(''); setResults([]); }} className="text-slate-400 hover:text-slate-600">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      {show && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-xl bg-white border border-slate-200 shadow-xl overflow-hidden max-h-80 overflow-y-auto">
          {results.map((r, i) => (
            <button
              key={i}
              className="w-full text-left px-4 py-2.5 hover:bg-slate-100 flex items-center justify-between transition-colors"
              onClick={() => { onSelect(r.stockCode, r.corpName); setQuery(''); setShow(false); }}
            >
              <span className="text-sm text-slate-900">{r.corpName}</span>
              <span className="text-xs text-slate-500 font-mono">{r.stockCode}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── PopularChips ──
function PopularChips({ onSelect }: { onSelect: (code: string, name: string) => void }) {
  const [chips, setChips] = useState<any[]>([]);
  useEffect(() => {
    dwFetch<any[]>('/popular').then(setChips).catch(() => {});
  }, []);
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap justify-center gap-2 mt-4">
      <span className="text-xs text-slate-400 flex items-center gap-1">
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
        인기
      </span>
      {chips.map(c => (
        <button key={c.stockCode}
          className="px-3 py-1 text-xs rounded-full bg-slate-100 text-slate-600 hover:bg-blue-500/20 hover:text-blue-400 transition-all border border-slate-200 hover:border-blue-500/30"
          onClick={() => onSelect(c.stockCode, c.corpName)}
        >{c.corpName}</button>
      ))}
    </div>
  );
}

// ── TabNavigation ──
const TABS = [
  { id: 'overview', label: '기업개요', icon: '🏢' },
  { id: 'financial', label: '재무데이터', icon: '📊' },
  { id: 'disclosure', label: '공시분석', icon: '📄' },
  { id: 'valuation', label: '밸류에이션', icon: '🧮' },
];

function TabNav({ active, onChange }: { active: string; onChange: (t: string) => void }) {
  return (
    <div className="flex gap-1 p-1 rounded-xl bg-slate-50 border border-slate-200">
      {TABS.map(t => (
        <button key={t.id}
          className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            active === t.id ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100 border border-transparent'
          }`}
          onClick={() => onChange(t.id)}
        >
          <span className="mr-1">{t.icon}</span>{t.label}
        </button>
      ))}
    </div>
  );
}

// ── CompanyOverview ──
function CompanyOverview({ data }: { data: any }) {
  const { company, stockPrice, dividend, priceHistory } = data;
  const priceUp = stockPrice.change >= 0;

  const infoItems = [
    { label: '기업명', value: `${company.corpName} (${company.corpNameEng || '-'})`, icon: '🏢' },
    { label: 'CEO', value: company.ceoName || '-', icon: '👤' },
    { label: '주소', value: company.address || '-', icon: '📍' },
    { label: '홈페이지', value: company.homepage || '-', icon: '🌐', link: company.homepage },
    { label: '설립일', value: formatDate(company.estDt), icon: '📅' },
    { label: '배당금/수익률', value: `${formatPrice(dividend.dps)} / ${formatPercent(dividend.dividendYield)}`, icon: '💰' },
  ];

  const chartData = priceHistory?.dates?.map((d: string, i: number) => ({
    date: d, price: priceHistory.closes[i],
  })) || [];

  return (
    <div className="space-y-6">
      {/* Stock Price Card */}
      <div className="p-5 rounded-xl bg-white border border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-2xl font-bold text-slate-900">{formatPrice(stockPrice.current)}</div>
            <div className={`text-sm font-medium ${priceUp ? 'text-green-400' : 'text-red-400'}`}>
              {priceUp ? '▲' : '▼'} {Math.abs(stockPrice.change)}%
            </div>
          </div>
          <div className="text-right text-xs text-slate-500 space-y-1">
            <div>시가총액: {formatKRW(stockPrice.marketCap)}</div>
            <div>거래량: {(stockPrice.volume || 0).toLocaleString()}</div>
          </div>
        </div>
        {chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => v.slice(5)} interval={Math.floor(chartData.length / 6)} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={['auto', 'auto']} tickFormatter={v => formatKRW(v)} />
              <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8 }}
                labelStyle={{ color: '#64748b' }} formatter={(v: any) => [formatPrice(v), '종가']} />
              <Line type="monotone" dataKey="price" stroke={COLORS.accent} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {infoItems.map((item, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-slate-50/50 border border-slate-200">
            <span className="text-lg">{item.icon}</span>
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">{item.label}</div>
              {item.link ? (
                <a href={item.link.startsWith('http') ? item.link : `http://${item.link}`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:underline truncate block">{item.value}</a>
              ) : (
                <div className="text-sm text-slate-700 truncate">{item.value}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── FinancialData ──
function FinancialData({ data }: { data: any }) {
  const { financials } = data;
  const barData = financials.years.map((yr: string, i: number) => ({
    year: yr,
    매출액: financials.revenue[i],
    영업이익: financials.operatingProfit[i],
    당기순이익: financials.netIncome[i],
  }));

  const latestIdx = financials.years.length - 1;
  const equity = financials.totalEquity[latestIdx] || 0;
  const debt = financials.totalDebt[latestIdx] || 0;
  const pieData = [
    { name: '자본총계', value: equity },
    { name: '부채총계', value: debt },
  ].filter(d => d.value > 0);

  const rows = [
    { label: '매출액', key: 'revenue' },
    { label: '영업이익', key: 'operatingProfit' },
    { label: '당기순이익', key: 'netIncome' },
    { label: '자산총계', key: 'totalAssets' },
    { label: '자본총계', key: 'totalEquity' },
    { label: '부채총계', key: 'totalDebt' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart */}
        <div className="p-5 rounded-xl bg-white border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">연간 실적 추이</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => formatKRW(v)} />
              <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8 }}
                formatter={(v: any) => [formatKRW(v)]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="매출액" fill={COLORS.accent} radius={[4, 4, 0, 0]} />
              <Bar dataKey="영업이익" fill={COLORS.green} radius={[4, 4, 0, 0]} />
              <Bar dataKey="당기순이익" fill={COLORS.amber} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart */}
        <div className="p-5 rounded-xl bg-white border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">자본/부채 구조 ({financials.years[latestIdx]})</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" outerRadius={90} dataKey="value"
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  labelLine={{ stroke: '#64748b' }}>
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8 }}
                  formatter={(v: any) => [formatKRW(v)]} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[260px] text-slate-400 text-sm">데이터 없음</div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="p-5 rounded-xl bg-white border border-slate-200 overflow-x-auto">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">재무 요약</h3>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 text-slate-500 font-medium">항목</th>
              {financials.years.map((yr: string) => (
                <th key={yr} className="text-right py-2 text-slate-500 font-medium">{yr}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.key} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 text-slate-600 font-medium">{r.label}</td>
                {(financials[r.key] as number[]).map((v: number, i: number) => (
                  <td key={i} className="py-2 text-right text-slate-700 font-mono">{formatKRW(v)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── DisclosureChart ──
function DisclosureTab({ stockCode }: { stockCode: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true); setError('');
    dwFetch<any>(`/disclosure-chart?stockCode=${stockCode}`)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [stockCode]);

  if (loading) return <LoadingSpinner text="공시 데이터 로딩 중..." />;
  if (error) return <ErrorCard message={error} />;
  if (!data) return null;

  const monthlyData = data.monthly.labels.map((l: string, i: number) => ({ month: l, count: data.monthly.counts[i] }));
  const typeData = data.byType.labels.map((l: string, i: number) => ({ name: l, value: data.byType.counts[i] }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl bg-white border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">월별 공시 건수</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#64748b' }} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8 }} />
              <Bar dataKey="count" fill={COLORS.accent} radius={[3, 3, 0, 0]} name="건수" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="p-5 rounded-xl bg-white border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">공시 유형별 분포</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={typeData} cx="50%" cy="50%" outerRadius={80} dataKey="value"
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#64748b' }}>
                {typeData.map((_: any, i: number) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Disclosures */}
      <div className="p-5 rounded-xl bg-white border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">최근 공시</h3>
        <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
          {data.recentDisclosures.map((d: any, i: number) => (
            <a key={i} href={d.link} target="_blank" rel="noopener noreferrer"
              className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors group">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-slate-400">📄</span>
                <span className="text-xs text-slate-600 truncate group-hover:text-blue-400">{d.title}</span>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{d.type}</span>
                <span className="text-[10px] text-slate-400">{d.date}</span>
                <svg className="w-3 h-3 text-slate-400 group-hover:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── ValuationModels ──
function ValuationTab({ stockCode }: { stockCode: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true); setError('');
    dwFetch<any>(`/valuation-models?stockCode=${stockCode}`)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [stockCode]);

  if (loading) return <LoadingSpinner text="밸류에이션 분석 중..." />;
  if (error) return <ErrorCard message={error} />;
  if (!data) return null;

  const { multiples, multiplesHistory, dcf, srim, grade } = data;

  const gradeColor = grade === '저평가' ? 'text-green-400 bg-green-500/10 border-green-500/30'
    : grade === '고평가' ? 'text-red-400 bg-red-500/10 border-red-500/30'
    : 'text-amber-400 bg-amber-500/10 border-amber-500/30';

  const metrics = [
    { label: 'PER', value: multiples.per, suffix: '배', color: multiples.per > 0 && multiples.per < 15 ? COLORS.green : COLORS.slate },
    { label: 'PBR', value: multiples.pbr, suffix: '배', color: multiples.pbr > 0 && multiples.pbr < 1.5 ? COLORS.green : COLORS.slate },
    { label: 'ROE', value: multiples.roe, suffix: '%', color: multiples.roe > 10 ? COLORS.green : COLORS.slate },
    { label: '부채비율', value: multiples.debtRatio, suffix: '%', color: multiples.debtRatio < 100 ? COLORS.green : COLORS.red },
    { label: '영업이익률', value: multiples.operatingMargin, suffix: '%', color: multiples.operatingMargin > 10 ? COLORS.green : COLORS.slate },
    { label: '순이익률', value: multiples.netMargin, suffix: '%', color: multiples.netMargin > 5 ? COLORS.green : COLORS.slate },
  ];

  const roeData = multiplesHistory.years.map((yr: string, i: number) => ({
    year: yr, ROE: multiplesHistory.roe[i],
  }));

  return (
    <div className="space-y-6">
      {/* Grade Badge */}
      <div className="flex justify-center">
        <span className={`text-lg font-bold px-5 py-2 rounded-full border ${gradeColor}`}>
          {grade === '저평가' ? '📈' : grade === '고평가' ? '📉' : '⚖️'} {grade}
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {metrics.map(m => (
          <div key={m.label} className="p-3 rounded-xl bg-white border border-slate-200 text-center">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">{m.label}</div>
            <div className="text-lg font-bold" style={{ color: m.color }}>
              {typeof m.value === 'number' ? m.value.toFixed(2) : '-'}
            </div>
            <div className="text-[10px] text-slate-400">{m.suffix}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* DCF */}
        <div className="p-5 rounded-xl bg-white border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">DCF 모델</h3>
          {dcf.fairValue ? (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">적정가치</span>
                <span className="text-lg font-bold text-slate-900">{formatPrice(dcf.fairValue)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">현재가</span>
                <span className="text-sm text-slate-600">{formatPrice(dcf.currentPrice)}</span>
              </div>
              {dcf.upside !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-500">상승여력</span>
                  <span className={`text-sm font-bold ${dcf.upside > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {dcf.upside > 0 ? '+' : ''}{dcf.upside}%
                  </span>
                </div>
              )}
              <div className="mt-3 pt-3 border-t border-slate-200 space-y-1">
                <div className="text-[10px] text-slate-400">가정</div>
                <div className="text-[11px] text-slate-500">성장률: {dcf.assumptions?.growthRate}% / 할인율: {dcf.assumptions?.discountRate}% / 영구성장률: {dcf.assumptions?.terminalGrowthRate}%</div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-400 text-center py-6">데이터 부족으로 산출 불가</div>
          )}
        </div>

        {/* S-RIM */}
        <div className="p-5 rounded-xl bg-white border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">S-RIM 모델</h3>
          {srim.fairValue ? (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">적정가치</span>
                <span className="text-lg font-bold text-slate-900">{formatPrice(srim.fairValue)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">현재가</span>
                <span className="text-sm text-slate-600">{formatPrice(srim.currentPrice)}</span>
              </div>
              {srim.upside !== undefined && (
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-500">상승여력</span>
                  <span className={`text-sm font-bold ${srim.upside > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {srim.upside > 0 ? '+' : ''}{srim.upside}%
                  </span>
                </div>
              )}
              <div className="mt-3 pt-3 border-t border-slate-200 space-y-1">
                <div className="text-[10px] text-slate-400">가정</div>
                <div className="text-[11px] text-slate-500">ROE: {srim.assumptions?.roe}% / 요구수익률: {srim.assumptions?.requiredReturn}% / BPS: {formatPrice(srim.assumptions?.bps)}</div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-400 text-center py-6">데이터 부족으로 산출 불가</div>
          )}
        </div>
      </div>

      {/* ROE History Chart */}
      {roeData.length > 0 && (
        <div className="p-5 rounded-xl bg-white border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">ROE 추이</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={roeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => `${v}%`} />
              <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8 }}
                formatter={(v: any) => [`${v}%`, 'ROE']} />
              <Line type="monotone" dataKey="ROE" stroke={COLORS.green} strokeWidth={2} dot={{ r: 4, fill: COLORS.green }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ── Shared small components ──
function LoadingSpinner({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="w-8 h-8 border-3 border-blue-400 border-t-transparent rounded-full animate-spin mr-3" />
      <span className="text-slate-500">{text}</span>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="text-center py-12 px-6 rounded-xl bg-red-500/5 border border-red-500/20">
      <p className="text-red-400">{message}</p>
    </div>
  );
}

// ── Main Page ──
export default function DartwingsPage() {
  const [selected, setSelected] = useState<{ stockCode: string; corpName: string } | null>(null);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  const handleSelect = useCallback((stockCode: string, corpName: string) => {
    setSelected({ stockCode, corpName });
    setActiveTab('overview');
    setLoading(true);
    setError('');
    setData(null);
    dwFetch<any>(`/analyze?stockCode=${stockCode}`)
      .then(setData)
      .catch(e => setError(e.message || '분석 데이터를 불러오는데 실패했습니다.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <span className="text-2xl">📊</span>
          <h1 className="text-xl font-bold text-slate-900">DartWings</h1>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">BETA</span>
        </div>
        <p className="text-sm text-slate-500 mb-6">DART 전자공시 기반 기업 분석 도구</p>
        <SearchBar onSelect={handleSelect} />
        <PopularChips onSelect={handleSelect} />
      </div>

      {/* Dashboard */}
      {selected && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-slate-900">
            {selected.corpName}
            <span className="text-xs font-normal text-slate-500 ml-2">({selected.stockCode})</span>
          </h2>

          {loading ? (
            <LoadingSpinner text={`${selected.corpName} 분석 중...`} />
          ) : error ? (
            <div className="text-center py-12">
              <ErrorCard message={error} />
              <button className="mt-4 px-4 py-2 rounded-lg bg-blue-500 text-white text-sm hover:bg-blue-600 transition-colors"
                onClick={() => handleSelect(selected.stockCode, selected.corpName)}>다시 시도</button>
            </div>
          ) : data ? (
            <>
              <TabNav active={activeTab} onChange={setActiveTab} />
              <div className="mt-4">
                {activeTab === 'overview' && <CompanyOverview data={data} />}
                {activeTab === 'financial' && <FinancialData data={data} />}
                {activeTab === 'disclosure' && <DisclosureTab stockCode={selected.stockCode} />}
                {activeTab === 'valuation' && <ValuationTab stockCode={selected.stockCode} />}
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
