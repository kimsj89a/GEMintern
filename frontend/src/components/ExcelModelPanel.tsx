import { useState, useRef } from 'react';
import { api } from '../api/client';

interface Tranche {
  name: string;
  type: string;
  amount: number | null;
  coupon_rate: number | null;
  ytm_base: number | null;
  ytm_stepup_per_year: number | null;
  maturity_years: number | null;
  dividend_rate: number | null;
  call_year: number | null;
  put_year: number | null;
}

interface DealStructure {
  company_name: string;
  investor_name: string;
  total_amount: number | null;
  investment_date: string | null;
  max_maturity_years: number | null;
  tranches: Tranche[];
  irr_guarantee: { rate: number | null; settlement: string | null } | null;
  exit_scenarios: { name: string; exit_year: number; multiple: number }[];
  covenants: { category: string; description: string }[];
  projections: {
    years: number[];
    revenue: number[];
    ebitda: number[];
    net_income: number[];
  } | null;
}

type Step = 'idle' | 'extracting' | 'preview' | 'building' | 'done';

export default function ExcelModelPanel({ projectName }: { projectName: string }) {
  const [step, setStep] = useState<Step>('idle');
  const [structure, setStructure] = useState<DealStructure | null>(null);
  const [excelB64, setExcelB64] = useState('');
  const [filename, setFilename] = useState('');
  const [error, setError] = useState('');
  const cancelledRef = useRef(false);

  const pollTask = async (taskId: string): Promise<any> => {
    return new Promise((resolve, reject) => {
      let retries = 0;
      const check = async () => {
        if (cancelledRef.current) { reject(new Error('cancelled')); return; }
        try {
          const s = await api.getTaskStatus(taskId);
          if (s.status === 'complete') resolve(s.result);
          else if (s.status === 'error') reject(new Error(s.error || '생성 실패'));
          else setTimeout(check, 2000);
        } catch (err) {
          retries++;
          if (retries > 3) reject(err);
          else setTimeout(check, 3000);
        }
      };
      check();
    });
  };

  const handleExtract = async () => {
    if (!projectName) return;
    setStep('extracting');
    setError('');
    cancelledRef.current = false;

    try {
      const { task_id } = await api.generateExcelModel(projectName);
      const result = await pollTask(task_id);

      setStructure(result.structure);
      setExcelB64(result.excel_b64);
      setFilename(result.filename);
      setStep('done');
    } catch (err: any) {
      if (err.message !== 'cancelled') {
        setError(err.message);
        setStep('idle');
      }
    }
  };

  const handleReset = () => {
    setStep('idle');
    setStructure(null);
    setExcelB64('');
    setFilename('');
    setError('');
  };

  const handleDownloadDirect = () => {
    if (!excelB64) return;
    const byteChars = atob(excelB64);
    const byteNums = new Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteNums[i] = byteChars.charCodeAt(i);
    }
    const blob = new Blob([new Uint8Array(byteNums)], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'CashFlow_Model.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Idle state */}
        {step === 'idle' && (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-50 flex items-center justify-center text-3xl">
              📊
            </div>
            <div className="text-center">
              <div className="text-sm font-medium text-slate-600 mb-1">Excel 캐시플로우 모델</div>
              <div className="text-xs text-slate-400 max-w-xs leading-relaxed">
                위키와 소스 문서에서 투자구조를 추출하여
                PEF 스타일 캐시플로우 Excel 모델을 자동 생성합니다.
              </div>
              <div className="text-xs text-slate-300 mt-2">
                Term Sheet, 투자계약서 등 투자구조 문서가 필요합니다
              </div>
            </div>
            <button
              onClick={handleExtract}
              disabled={!projectName}
              className="px-6 py-2.5 bg-emerald-600 text-white text-sm font-medium rounded-xl hover:bg-emerald-700 disabled:opacity-30 transition-colors"
            >
              모델 생성
            </button>
          </div>
        )}

        {/* Extracting */}
        {step === 'extracting' && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="w-12 h-12 border-3 border-emerald-400 border-t-transparent rounded-full animate-spin" />
            <div className="text-center">
              <div className="text-sm font-medium text-slate-600">투자구조 분석 중...</div>
              <div className="text-xs text-slate-400 mt-1">위키 + 소스 문서에서 투자 조건을 추출하고 있습니다</div>
            </div>
            <button
              onClick={() => { cancelledRef.current = true; setStep('idle'); }}
              className="px-4 py-1.5 text-xs text-red-500 border border-red-200 rounded-lg hover:bg-red-50"
            >
              취소
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Done — structure preview + download */}
        {step === 'done' && structure && (
          <>
            {/* Download bar */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xl">✅</span>
                <div>
                  <div className="text-sm font-medium text-emerald-800">{filename}</div>
                  <div className="text-xs text-emerald-600">Excel 모델 생성 완료</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownloadDirect}
                  className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors"
                >
                  다운로드
                </button>
                <button
                  onClick={handleReset}
                  className="px-3 py-2 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50"
                >
                  재생성
                </button>
              </div>
            </div>

            {/* Structure preview */}
            <div className="space-y-3">
              {/* Basic info */}
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100">
                  <span className="text-sm font-semibold text-slate-700">기본 정보</span>
                </div>
                <div className="px-4 py-3 grid grid-cols-2 gap-3 text-sm">
                  <InfoItem label="대상회사" value={structure.company_name} />
                  <InfoItem label="투자자" value={structure.investor_name} />
                  <InfoItem label="총 투자규모" value={structure.total_amount ? `${structure.total_amount}억원` : '-'} />
                  <InfoItem label="투자일자" value={structure.investment_date || '-'} />
                  <InfoItem label="최장 만기" value={structure.max_maturity_years ? `${structure.max_maturity_years}년` : '-'} />
                  {structure.irr_guarantee?.rate && (
                    <InfoItem label="IRR 보장" value={`${structure.irr_guarantee.rate}%`} />
                  )}
                </div>
              </div>

              {/* Tranches */}
              {structure.tranches.map((tr, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                      {tr.type}
                    </span>
                    <span className="text-sm font-semibold text-slate-700">{tr.name}</span>
                  </div>
                  <div className="px-4 py-3 grid grid-cols-3 gap-3 text-sm">
                    <InfoItem label="금액" value={tr.amount ? `${tr.amount}억원` : '-'} />
                    <InfoItem label="Coupon" value={tr.coupon_rate != null ? `${tr.coupon_rate}%` : '-'} />
                    <InfoItem label="YTM Base" value={tr.ytm_base != null ? `${tr.ytm_base}%` : '-'} />
                    <InfoItem label="Step-up" value={tr.ytm_stepup_per_year != null ? `+${tr.ytm_stepup_per_year}%/yr` : '-'} />
                    <InfoItem label="만기" value={tr.maturity_years ? `${tr.maturity_years}년` : '-'} />
                    {tr.dividend_rate != null && tr.dividend_rate > 0 && (
                      <InfoItem label="우선배당" value={`${tr.dividend_rate}%`} />
                    )}
                    {tr.call_year != null && tr.call_year > 0 && (
                      <InfoItem label="Call" value={`Y${tr.call_year}`} />
                    )}
                    {tr.put_year != null && tr.put_year > 0 && (
                      <InfoItem label="Put" value={`Y${tr.put_year}`} />
                    )}
                  </div>
                </div>
              ))}

              {/* Exit scenarios */}
              {structure.exit_scenarios.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100">
                    <span className="text-sm font-semibold text-slate-700">Exit 시나리오</span>
                  </div>
                  <div className="px-4 py-3">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-slate-500 border-b border-slate-100">
                          <th className="text-left py-1.5 font-medium">시나리오</th>
                          <th className="text-right py-1.5 font-medium">Exit Year</th>
                          <th className="text-right py-1.5 font-medium">Multiple</th>
                        </tr>
                      </thead>
                      <tbody>
                        {structure.exit_scenarios.map((s, i) => (
                          <tr key={i} className="border-b border-slate-50">
                            <td className="py-1.5 text-slate-700">{s.name}</td>
                            <td className="py-1.5 text-right text-slate-600">Y{s.exit_year}</td>
                            <td className="py-1.5 text-right font-medium text-blue-700">{s.multiple}x</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Covenants */}
              {structure.covenants.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100">
                    <span className="text-sm font-semibold text-slate-700">Covenants</span>
                  </div>
                  <div className="px-4 py-3 space-y-2">
                    {structure.covenants.map((c, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 shrink-0 mt-0.5">
                          {c.category}
                        </span>
                        <span className="text-slate-700">{c.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Projections */}
              {structure.projections && structure.projections.years.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100">
                    <span className="text-sm font-semibold text-slate-700">Financial Projections</span>
                  </div>
                  <div className="px-4 py-3 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-slate-500 border-b border-slate-100">
                          <th className="text-left py-1.5 font-medium">항목</th>
                          {structure.projections.years.map(y => (
                            <th key={y} className="text-right py-1.5 font-medium">{y}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {structure.projections.revenue?.length > 0 && (
                          <tr className="border-b border-slate-50">
                            <td className="py-1.5 text-slate-700">매출</td>
                            {structure.projections.revenue.map((v, i) => (
                              <td key={i} className="py-1.5 text-right text-slate-600">{v}</td>
                            ))}
                          </tr>
                        )}
                        {structure.projections.ebitda?.length > 0 && (
                          <tr className="border-b border-slate-50">
                            <td className="py-1.5 text-slate-700">EBITDA</td>
                            {structure.projections.ebitda.map((v, i) => (
                              <td key={i} className="py-1.5 text-right text-slate-600">{v}</td>
                            ))}
                          </tr>
                        )}
                        {structure.projections.net_income?.length > 0 && (
                          <tr className="border-b border-slate-50">
                            <td className="py-1.5 text-slate-700">순이익</td>
                            {structure.projections.net_income.map((v, i) => (
                              <td key={i} className="py-1.5 text-right text-slate-600">{v}</td>
                            ))}
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}


function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-slate-700 font-medium">{value}</div>
    </div>
  );
}
