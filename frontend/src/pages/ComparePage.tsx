/**
 * ComparePage — Standalone contract comparison (direct file upload mode).
 * No project needed. Upload two files and compare.
 */
import ContractComparePanel from '../components/ContractComparePanel';

export default function ComparePage() {
  return (
    <div className="h-full flex flex-col">
      <div className="px-6 pt-5 pb-2">
        <h1 className="text-xl font-bold text-slate-800">⚖️ 신구조문 비교</h1>
        <p className="text-sm text-slate-400 mt-0.5">원본과 비교 파일을 직접 업로드하여 비교 분석</p>
      </div>
      <div className="flex-1 overflow-hidden">
        <ContractComparePanel projectName="__standalone__" selectedDocs={[]} />
      </div>
    </div>
  );
}
