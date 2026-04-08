/**
 * ComparePage — Standalone contract comparison.
 * StyleSeed design: full-screen layout with back button.
 */
import { useAppStore } from '../stores/appStore';
import ContractComparePanel from '../components/ContractComparePanel';

export default function ComparePage() {
  const backToDashboard = useAppStore(s => s.backToDashboard);

  return (
    <div className="h-screen flex flex-col bg-[#FAFAFA]" style={{ fontFamily: "'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      <header className="flex items-center gap-3 px-5 py-3 bg-white border-b border-slate-100 shadow-[0_1px_2px_rgba(0,0,0,0.04)] shrink-0">
        <button onClick={backToDashboard} className="text-[#9B9B9B] hover:text-[#3C3C3C] transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <div className="w-8 h-8 rounded-xl bg-amber-500 flex items-center justify-center text-white text-sm">⚖️</div>
        <div>
          <div className="text-sm font-bold text-[#2A2A2A]">신구조문 비교</div>
          <div className="text-[10px] text-[#9B9B9B]">원본 ↔ 비교 파일 분석</div>
        </div>
      </header>
      <div className="flex-1 overflow-hidden">
        <ContractComparePanel projectName="__standalone__" selectedDocs={[]} />
      </div>
    </div>
  );
}
