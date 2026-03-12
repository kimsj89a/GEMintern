import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import { subscribeTask, unsubscribeTask } from '../api/ws';
import FolderTree from '../components/FolderTree';
import FilePicker from '../components/FilePicker';
import ChatWidget from '../components/ChatWidget';
import type { ChatMessage } from '../components/ChatWidget';
import MarkdownViewer from '../components/MarkdownViewer';
import { copyRichText, downloadAsWord, generateFilename } from '../utils/clipboard';
import GenerationProgress from '../components/GenerationProgress';
import { getLocalFolderTree, addLocalDocuments } from '../utils/projectDB';
import { useAutoSync } from '../utils/autoSync';

/* ─── Types ─── */
type WriteMode = 'report' | 'ppt';
type Phase2View = 'choice' | 'templates' | 'generate' | 'refine' | 'result';

/* ─── Section definitions for section-selectable templates ─── */
interface TemplateSection {
  id: string;
  label: string;
  structure: string;
}

const INVESTMENT_SECTIONS: TemplateSection[] = [
  { id: 'inv1', label: '1. 투자내용', structure: `## 1. 투자내용\n### 1.1 투자개요\n### 1.2 투자 구조 및 재원\n### 1.3 주요 투자 조건 (Key Terms)\n### 1.4 예상사용계획\n### 1.5 투자 전/후 주주구성` },
  { id: 'inv2', label: '2. 회사현황', structure: `## 2. 회사현황\n### 2.1 회사개요\n### 2.2 회사연혁\n### 2.3 조직현황\n### 2.4 주요 경영진 현황\n### 2.5 기존 투자이력\n### 2.6 차입금 주주 현황\n### 2.7 재무현황` },
  { id: 'inv3', label: '3. 시장분석', structure: `## 3. 시장분석\n### 3.1 시장 현황 및 산업 매력도\n### 3.2 경쟁 환경 분석\n### 3.3 규제 및 정책 환경` },
  { id: 'inv4', label: '4. 사업분석', structure: `## 4. 사업분석\n### 4.1 사업개요 (비즈니스 모델)\n### 4.2 주요 제품 및 서비스\n### 4.3 특별 기술력 검토\n### 4.4 경쟁력 대비 차별화\n### 4.5 재무실적과 향후 매출 추정` },
  { id: 'inv5', label: '5. 투자 타당성 분석', structure: `## 5. 투자 타당성 분석\n### 5.1 Valuation 분석\n### 5.2 Value-up 방안\n### 5.3 Exit Scenario별 투자수익률` },
  { id: 'inv6', label: '6. 리스크 분석', structure: `## 6. 리스크 분석\n### 6.1 산업/사업 리스크\n### 6.2 재무/법률 리스크\n### 6.3 Exit 리스크` },
  { id: 'inv7', label: '7. 종합의견', structure: `## 7. 종합의견\n### 7.1 투자포인트\n### 7.2 투자우려요소\n### 7.3 종합의견` },
];

const TEMPLATE_SECTIONS: Record<string, TemplateSection[]> = {
  investment: INVESTMENT_SECTIONS,
};

/* ─── Template definitions ─── */
const REPORT_TEMPLATES = [
  { id: 'simple_review', label: '간단 검토', desc: '예비투자심의 Quick Memo', icon: '📋' },
  { id: 'free_summary', label: '자유 요약', desc: '자료 특성 맞춤 자유 구조화', icon: '📝' },
  { id: 'context_based', label: '컨텍스트 기반', desc: '사용자 지시 중심 보고서', icon: '🔍' },
  { id: 'investment', label: '투자 보고서', desc: '투자위원회 심의용', icon: '💰' },
  { id: 'management', label: '경영 분석', desc: '투자 후 경영관리 보고서', icon: '📊' },
  { id: 'term_sheet', label: 'Term Sheet', desc: '투자조건 요약서', icon: '📑' },
  { id: 'loi_mou', label: 'LOI/MOU', desc: '인수의향서 초안', icon: '🤝' },
  { id: 'im', label: 'IM 작성', desc: 'Investment Memorandum', icon: '📖' },
  { id: 'teaser', label: 'Teaser', desc: '1장짜리 딜 요약', icon: '🎯' },
  { id: 'dd_report', label: 'DD 보고서', desc: '실사결과보고서', icon: '🔬' },
];

const PPT_TEMPLATES = [
  { id: 'presentation', label: '발표자료', desc: '2-Column 투자 발표 슬라이드', icon: '📊' },
  { id: 'paper_review', label: '논문 발표자료', desc: '논문 구조 자동 인식 슬라이드', icon: '📄' },
];

const TEMPLATE_PREVIEWS: Record<string, string> = {
  simple_review: `# 1. 투자 개요
본 건은 [대상회사]에 대한 [투자 구조], 총 투자 규모가 **[000]억원**

---
# 2. 회사 및 사업 현황
## 2.1 기업 개요 (표)
## 2.2 비즈니스 모델 (BM)
## 2.3 과거 재무 실적 (표)
## 2.4 향후 추정 (표)

---
# 3. 투자조건 (Term Sheet) (표)

---
# 4. 투자포인트 (Investment Highlights)
(1) 검증된 성장성
(2) 차별화된 수익 구조
(3) 확정된 회수 로드맵

---
# 5. 예상 우려 요소
## 5.1 주요 리스크 대응
## 5.2 부채 및 상환 스케줄 분석

---
# 6. 향후 추진 일정 (표)`,

  free_summary: `(자유 구조화 요약 모드)

제공된 자료의 특성에 맞게 최적의 구조로 요약합니다.

### 권장 구조 (참고용)
- Executive Summary: 핵심 내용 3~5줄 요약
- 핵심 데이터: 주요 수치/지표 정리 (표 활용)
- 주요 내용: 카테고리별 상세 내용
- 시사점: 데이터에서 도출된 인사이트

※ 위 구조는 예시이며, 자료 특성에 따라 자유롭게 변형됩니다.`,

  context_based: `(컨텍스트 기반 작성 모드)

사용자가 입력한 지시사항을 중심으로 보고서를 작성합니다.

### 사용 방법
1. "추가 컨텍스트" 란에 원하는 보고서 구조/내용을 상세히 기술
2. 업로드된 자료에서 관련 내용을 자동 추출
3. 지시사항에 맞춰 맞춤형 보고서 생성

※ 자유도가 가장 높은 모드입니다.`,

  investment: `# 투자심사보고서: [대상기업명]

## 1. 투자내용
### 1.1 투자개요
### 1.2 투자 구조 및 재원
### 1.3 주요 투자 조건 (Key Terms)
### 1.4 예상사용계획
### 1.5 투자 전/후 주주구성

## 2. 회사현황
### 2.1~2.7 (회사개요, 연혁, 조직, 경영진, 투자이력, 차입금, 재무)

## 3. 시장분석
### 3.1~3.3 (시장현황, 경쟁환경, 규제)

## 4. 사업분석
### 4.1~4.5 (BM, 제품, 기술력, 차별화, 재무추정)

## 5. 투자 타당성 분석
### 5.1~5.3 (Valuation, Value-up, Exit 수익률)

## 6. 리스크 분석
### 6.1~6.3 (산업, 재무/법률, Exit)

## 7. 종합의견`,

  management: `# 1. 투자 현황 요약 (표)

---
# 2. 실적 추이 (Projection vs Actual)
## 2.1 손익 현황 (표: 예상 vs 실적 vs 달성률)
## 2.2 재무 상태 (표: 투자시 vs 현재)

---
# 3. KPI 달성 현황 (표)

---
# 4. 약정사항(Covenant) 준수 현황 (표)

---
# 5. 주요 이슈 및 대응
## 5.1 경영/사업 이슈
## 5.2 시장/규제 이슈
## 5.3 Value-up 진행 현황

---
# 6. Exit 전략 업데이트
## 6.1 시나리오별 예상 수익률 (표)
## 6.2 Exit 추진 현황
## 6.3 향후 계획`,

  term_sheet: `# Term Sheet Summary: [대상회사명]

## 1. Transaction Overview (거래 개요) - 표
## 2. Equity Terms (투자 조건) - 표
  투자형태, 발행가액, 전환조건, 리픽싱, 희석방지, 배당, 상환
## 3. Governance (지배구조) - 표
  이사회, 옵서버, 동의권, 정보접근권
## 4. Protective Provisions (투자자 보호) - 표
  Drag, Tag, ROFR, Put, 공동매도, 잔여재산분배
## 5. Exit (회수) - 표
  IPO 의무, 미달시, Lock-up, M&A
## 6. Others (기타) - 표
  경업금지, Key-man, R&W, 손해배상

## 협상 포인트 (Negotiation Points) - 표`,

  loi_mou: `# 인수의향서 (Letter of Intent)

※ AI 생성 초안 - 법률 전문가 검토 필수

## 전문 (Recitals)
## 제1조. 거래 구조 (Transaction Structure) - 표
## 제2조. 매매대금 (Purchase Price)
## 제3조. 실사 (Due Diligence)
## 제4조. 독점교섭권 (Exclusivity)
## 제5조. 선행조건 (Conditions Precedent)
## 제6조. 비밀유지 (Confidentiality) — 구속력 있음
## 제7조. 비용 부담 (Expenses) — 구속력 있음
## 제8조. 법적 구속력 (Binding Effect)
## 제9조. 유효기간 (Term)

서명란`,

  im: `# 1. Investment Highlights
## 1.1 핵심 투자 포인트 (3~5개)
## 1.2 거래 구조 요약 (Transaction Summary) - 표

---
# 2. Company Overview
## 2.1~2.4 (회사개요, 연혁, 경영진, 주주구성)

---
# 3. Market Analysis
## 3.1~3.4 (TAM/SAM/SOM, 산업동향, 경쟁환경, 규제)

---
# 4. Business & Product
## 4.1~4.4 (BM, 제품, 기술력, 고객/파트너)

---
# 5. Financial Overview
## 5.1 과거 재무 실적 (표)
## 5.2 향후 추정
## 5.3 Valuation 분석 (Peer Comparison)

---
# 6. Growth Strategy & Exit
## 6.1~6.3 (성장전략, 자금사용, Exit 시나리오)`,

  teaser: `# [대상회사명] — Investment Teaser

## Investment Highlights (3대 포인트)

---
## Company Snapshot (표)
## Market Opportunity (시장규모, 성장동력)
## Financial Summary (표: 매출/EBITDA/순이익)
## Proposed Transaction (표: 거래유형/규모/Valuation)

※ 1장짜리 딜 요약 문서`,

  dd_report: `# 실사결과보고서 (Due Diligence Report)

## 대상회사 / 실사유형 / 기간

---
# 1. Executive Summary
  발견사항 요약: Critical/Major/Minor 건수

---
# 2. 실사 범위 (Scope of Work) - 표
# 3. Key Findings
## 3.1 Critical Issues (즉시 대응 필요)
## 3.2 Major Issues (주의 필요)
## 3.3 Minor Issues (참고)

---
# 4. Issue List (이슈 목록 요약) - 표
# 5. Risk Assessment
## 5.1 Risk Matrix
## 5.2 가격 조정 요소 - 표

---
# 6. Recommendations (권고사항)`,

  presentation: `# 1. Executive Summary
## 투자 개요
## 특별 투자 포인트
## 주요 투자 조건

# 2. Company & Market
## 회사 개요
## 시장 현황
## 경쟁 환경

# 3. Business Analysis
## 비즈니스 모델
## 특별 기술/역량
## 재무 실적

# 4. Investment Analysis
## Valuation
## Exit 계획
## 예상 수익률

# 5. Risk & Conclusion
## 주요 리스크
## 종합 의견

※ 2-Column 투자 발표 슬라이드 형태로 생성`,

  paper_review: `(자동 구조 인식 모드)

업로드된 논문의 실제 섹션 구조를 자동 인식하여 슬라이드를 구성합니다.

### 일반적인 논문 구조
- Abstract → 1~2 슬라이드
- Introduction / Background → 2~3 슬라이드
- Method / Approach → 3~5 슬라이드
- Experiments / Results → 3~5 슬라이드
- Discussion → 1~2 슬라이드
- Conclusion → 1 슬라이드

※ 각 섹션의 내용 분량에 따라 슬라이드 개수가 자동 조절됩니다.`,
};

/* ─── Phase config ─── */
const PHASE_CONFIG: Record<string, { title: string; desc: string; steps: { id: number; label: string }[] }> = {
  phase1: {
    title: '사전 정보 수집',
    desc: '투자 대상 기업/자산의 기초 자료를 수집하고 분석합니다.',
    steps: [
      { id: 1, label: '자료 업로드' },
      { id: 2, label: '자료 분석' },
      { id: 3, label: '자료 Q&A' },
    ],
  },
  phase2: {
    title: '문서 작성',
    desc: '수집된 자료를 바탕으로 보고서 또는 PPT를 생성합니다.',
    steps: [],
  },
};

export default function WorkflowPage() {
  const { currentProject, activePage } = useAppStore();
  useAutoSync(currentProject);
  const phase = PHASE_CONFIG[activePage] || PHASE_CONFIG.phase2;
  const isPhase1 = activePage === 'phase1';

  const [step, setStep] = useState(1);
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [context, setContext] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [genStartTime, setGenStartTime] = useState(0);
  const [analysisResult, setAnalysisResult] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const [phase2View, setPhase2View] = useState<Phase2View>('choice');
  const [writeMode, setWriteMode] = useState<WriteMode>('report');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [selectedSections, setSelectedSections] = useState<string[]>([]);
  const [docsCollapsed, setDocsCollapsed] = useState(true);

  const cancelAnalyzeRef = useRef(false);
  const cancelGenerateRef = useRef(false);
  const cancelChatRef = useRef(false);
  const activeTaskRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!currentProject) return;
    getLocalFolderTree(currentProject).then(setTree).catch(() => setTree({}));
    // docs loaded from local IndexedDB
  }, [currentProject]);

  const handleUpload = async (files: File[]) => {
    if (!currentProject) return;
    setUploading(true);
    setUploadStatus('');
    try {
      const result = await api.parseFiles(files);
      const docs = Object.entries(result.parsed_texts).map(([filename, text]) => ({ filename, parsedText: text }));
      await addLocalDocuments(currentProject, docs);
      setUploadStatus(`${docs.length}개 파일 업로드 완료. 로컬에 저장됨.`);
      const t = await getLocalFolderTree(currentProject);
      setTree(t);
    } catch {
      setUploadStatus('업로드 실패');
    }
    setUploading(false);
  };

  const handleAnalyze = async () => {
    if (!currentProject) return;
    setAnalyzing(true);
    setAnalysisResult('');
    setStep(2);
    cancelAnalyzeRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'material_summary',
        kwargs: { project_name: currentProject, selected_docs: selectedDocs },
      });
      const check = async () => {
        if (cancelAnalyzeRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') { setAnalysisResult(status.result || ''); setAnalyzing(false); }
        else if (status.status === 'error') { setAnalysisResult(`오류: ${status.error}`); setAnalyzing(false); }
        else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) {
      setAnalysisResult(`오류: ${err.message}`);
      setAnalyzing(false);
    }
  };

  const handleStopAnalyze = () => { cancelAnalyzeRef.current = true; setAnalyzing(false); };

  const handlePhase1Chat = async (question: string) => {
    setChatMessages((prev) => [...prev, { role: 'user', content: question }]);
    setChatLoading(true);
    cancelChatRef.current = false;
    try {
      const { task_id } = await api.startQa({
        project_name: currentProject,
        question,
        selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
      });
      const check = async () => {
        if (cancelChatRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          setChatMessages((prev) => [...prev, { role: 'assistant', content: status.result || '' }]);
          setChatLoading(false);
        } else if (status.status === 'error') {
          setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${status.error}` }]);
          setChatLoading(false);
        } else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${err.message}` }]);
      setChatLoading(false);
    }
  };

  const handleStopChat = () => { cancelChatRef.current = true; setChatLoading(false); };

  const handleGenerate = async () => {
    if (!currentProject || !selectedTemplate) return;
    setGenerating(true);
    setStreamingText('');
    setResult('');
    setPhase2View('generate');
    setGenStartTime(Date.now());
    cancelGenerateRef.current = false;
    const mode = selectedTemplate === 'im' ? 'chained' : 'single';
    // Build custom structure_text from selected sections
    const sections = TEMPLATE_SECTIONS[selectedTemplate];
    let structureText = '';
    if (sections && selectedSections.length > 0 && selectedSections.length < sections.length) {
      const filtered = sections.filter(s => selectedSections.includes(s.id));
      structureText = `# 투자심사보고서: [대상기업명]\n\n` + filtered.map(s => s.structure).join('\n\n');
    }
    try {
      const { task_id } = await api.startGenerate({
        project_name: currentProject,
        template_option: selectedTemplate,
        thinking_level: 'MEDIUM',
        file_context: '',
        inputs: { selected_docs: selectedDocs, ...(structureText ? { structure_text: structureText } : {}) },
        mode,
      });
      activeTaskRef.current = task_id;
      subscribeTask(task_id, (msg) => {
        if (cancelGenerateRef.current) { unsubscribeTask(task_id); return; }
        if (msg.type === 'chunk' && msg.data) setStreamingText((prev) => prev + msg.data);
        else if (msg.type === 'complete') { setResult(msg.result || ''); setStreamingText(''); setGenerating(false); unsubscribeTask(task_id); }
        else if (msg.type === 'error') { setResult(`오류: ${msg.error}`); setStreamingText(''); setGenerating(false); unsubscribeTask(task_id); }
      });
      pollRef.current = setInterval(async () => {
        if (cancelGenerateRef.current) { if (pollRef.current) clearInterval(pollRef.current); return; }
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete' && !result) { if (pollRef.current) clearInterval(pollRef.current); setResult(status.result || ''); setStreamingText(''); setGenerating(false); }
        else if (status.status === 'error' && !result) { if (pollRef.current) clearInterval(pollRef.current); setResult(`오류: ${status.error}`); setStreamingText(''); setGenerating(false); }
      }, 3000);
      setTimeout(() => { if (pollRef.current) clearInterval(pollRef.current); }, 600000);
    } catch (err: any) { setResult(`오류: ${err.message}`); setGenerating(false); }
  };

  const handleStopGenerate = () => {
    cancelGenerateRef.current = true;
    if (activeTaskRef.current) unsubscribeTask(activeTaskRef.current);
    if (pollRef.current) clearInterval(pollRef.current);
    if (streamingText) setResult(streamingText);
    setStreamingText('');
    setGenerating(false);
  };

  const handleRefine = async (feedback: string) => {
    setChatMessages((prev) => [...prev, { role: 'user', content: feedback }]);
    setChatLoading(true);
    cancelChatRef.current = false;
    try {
      const { task_id } = await api.startAnalysis({
        task_type: 'refine',
        kwargs: { current_text: result, chat_history: chatMessages, refine_query: feedback, additional_file_context: '' },
      });
      const check = async () => {
        if (cancelChatRef.current) return;
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') { setResult(status.result || ''); setChatMessages((prev) => [...prev, { role: 'assistant', content: '보고서가 수정되었습니다.' }]); setChatLoading(false); }
        else if (status.status === 'error') { setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${status.error}` }]); setChatLoading(false); }
        else setTimeout(check, 1000);
      };
      check();
    } catch (err: any) { setChatMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${err.message}` }]); setChatLoading(false); }
  };

  const downloadMarkdown = () => {
    const text = result || analysisResult;
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = generateFilename(activePage || '자료분석', 'md', currentProject); a.click();
    URL.revokeObjectURL(url);
  };

  if (!currentProject) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <h1 className="text-xl font-bold text-slate-800 mb-2">{phase.title}</h1>
        <div className="flex flex-col items-center py-16 text-slate-400">
          <svg className="w-12 h-12 mb-3 opacity-30" viewBox="0 0 24 24" fill="none"><path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" stroke="currentColor" strokeWidth="1.5"/></svg>
          <span className="text-sm">프로젝트를 먼저 선택하세요.</span>
        </div>
      </div>
    );
  }

  const currentTemplates = writeMode === 'report' ? REPORT_TEMPLATES : PPT_TEMPLATES;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-5 animate-fade-in">
        <h1 className="text-xl font-bold text-slate-800 tracking-tight">{phase.title}</h1>
        <p className="text-sm text-slate-500 mt-0.5">{phase.desc}</p>
      </div>

      {/* Step indicator - Phase 1 only */}
      {isPhase1 && (
        <div className="flex items-center gap-1.5 mb-6">
          {phase.steps.map((s, i) => (
            <div key={s.id} className="flex items-center">
              <button
                onClick={() => !generating && !analyzing && setStep(s.id)}
                className={`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 ${
                  step === s.id
                    ? 'btn-primary shadow-sm'
                    : step > s.id
                      ? 'bg-blue-50 text-blue-600'
                      : 'bg-slate-100 text-slate-400'
                }`}
              >
                {s.id}. {s.label}
              </button>
              {i < phase.steps.length - 1 && (
                <svg className="w-4 h-4 mx-1 text-slate-300" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ======================== PHASE 1 ======================== */}
      {isPhase1 && step === 1 && (
        <div className="space-y-4 animate-fade-in-up">
          <div className="flex gap-4">
            <div className="w-64 shrink-0 glass-card p-3 max-h-80 overflow-y-auto">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">프로젝트 문서</div>
              <FolderTree tree={tree} projectName={currentProject} selectable selectedDocs={selectedDocs} onSelectionChange={setSelectedDocs} />
            </div>
            <div className="flex-1 space-y-4">
              <div className="glass-card p-4">
                <label className="block text-sm font-semibold text-slate-700 mb-2">추가 자료 업로드</label>
                <FilePicker onFilesSelected={handleUpload} loading={uploading} />
                {uploadStatus && <div className="mt-2 text-sm text-slate-500">{uploadStatus}</div>}
              </div>
              <button onClick={handleAnalyze}
                className="w-full py-3 btn-primary rounded-xl text-sm">
                자료 분석 시작
              </button>
            </div>
          </div>
        </div>
      )}

      {isPhase1 && step === 2 && (
        <div className="glass-card-elevated p-6 animate-fade-in-up">
          {analyzing && (
            <div className="flex items-center gap-3 mb-3">
              <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-slate-500">분석 중...</span>
              <button onClick={handleStopAnalyze}
                className="px-3 py-1 bg-red-500 text-white text-xs font-semibold rounded-lg hover:bg-red-600 transition-all">
                중지
              </button>
            </div>
          )}
          <div className="max-h-[60vh] overflow-y-auto">
            <MarkdownViewer content={analysisResult} />
          </div>
          {!analyzing && analysisResult && (
            <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
              <button onClick={() => setStep(3)} className="px-4 py-2 btn-primary text-sm rounded-lg">자료 Q&A</button>
              <button onClick={() => downloadAsWord(analysisResult, generateFilename('자료분석', 'docx', currentProject))} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">Word 저장</button>
              <button onClick={downloadMarkdown} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">MD 저장</button>
            </div>
          )}
        </div>
      )}

      {isPhase1 && step === 3 && (
        <div className="flex gap-4 animate-fade-in-up" style={{ height: 'calc(100vh - 280px)' }}>
          <div className="flex-1 glass-card-elevated p-5 overflow-y-auto">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">분석 결과</div>
            <MarkdownViewer content={analysisResult} />
          </div>
          <div className="w-96 glass-card-elevated p-4 flex flex-col">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">자료 기반 Q&A</div>
            <ChatWidget messages={chatMessages} onSend={handlePhase1Chat} loading={chatLoading} onStop={handleStopChat} placeholder="자료에 대해 질문하세요..." />
          </div>
        </div>
      )}

      {/* ======================== PHASE 2: Choice ======================== */}
      {!isPhase1 && phase2View === 'choice' && (
        <div className="flex items-center justify-center animate-fade-in-up" style={{ minHeight: 'calc(100vh - 280px)' }}>
          <div className="flex gap-6">
            <button
              onClick={() => { setWriteMode('report'); setSelectedTemplate(''); setPhase2View('templates'); }}
              className="group w-72 glass-card-elevated p-8 flex flex-col items-center gap-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-blue-500 to-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-300"
                style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))' }}>
                📄
              </div>
              <div>
                <div className="text-lg font-bold text-slate-800">보고서 작성</div>
                <div className="text-sm text-slate-500 mt-1">투심보고서, IM, Term Sheet 등</div>
                <div className="text-xs text-blue-500 font-semibold mt-2">10종 템플릿</div>
              </div>
            </button>
            <button
              onClick={() => { setWriteMode('ppt'); setSelectedTemplate(''); setPhase2View('templates'); }}
              className="group w-72 glass-card-elevated p-8 flex flex-col items-center gap-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-violet-500 to-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-300"
                style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.1), rgba(59,130,246,0.1))' }}>
                📊
              </div>
              <div>
                <div className="text-lg font-bold text-slate-800">PPT 작성</div>
                <div className="text-sm text-slate-500 mt-1">투자 발표, 논문 발표</div>
                <div className="text-xs text-violet-500 font-semibold mt-2">2종 템플릿</div>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* ======================== PHASE 2: Templates ======================== */}
      {!isPhase1 && phase2View === 'templates' && (
        <div className="animate-fade-in-up">
          <button
            onClick={() => setPhase2View('choice')}
            className="mb-4 flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all"
          >
            <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none"><path d="M10 4L6 8l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
            돌아가기
          </button>

          <div className="flex gap-5" style={{ minHeight: 'calc(100vh - 340px)' }}>
            {/* Left panel */}
            <div className="w-[480px] shrink-0 space-y-4 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 340px)' }}>
              {/* Template grid */}
              <div className="glass-card p-4">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">
                  {writeMode === 'report' ? '보고서 템플릿' : 'PPT 템플릿'}
                </div>
                <div className={`grid gap-2 stagger-children ${writeMode === 'report' ? 'grid-cols-2' : 'grid-cols-1'}`}>
                  {currentTemplates.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        setSelectedTemplate(t.id);
                        const sections = TEMPLATE_SECTIONS[t.id];
                        if (sections) setSelectedSections(sections.map(s => s.id));
                        else setSelectedSections([]);
                      }}
                      className={`text-left p-3 rounded-xl border transition-all duration-200 group ${
                        selectedTemplate === t.id
                          ? 'border-blue-300 bg-blue-50/70 shadow-sm'
                          : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50/50'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-base group-hover:scale-110 transition-transform">{t.icon}</span>
                        <span className={`text-sm font-semibold ${selectedTemplate === t.id ? 'text-blue-700' : 'text-slate-700'}`}>{t.label}</span>
                      </div>
                      <div className="text-xs text-slate-400 pl-7">{t.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Document selection */}
              <div className="glass-card overflow-hidden">
                <button
                  onClick={() => setDocsCollapsed(!docsCollapsed)}
                  className="w-full flex items-center justify-between p-3.5 text-sm font-semibold text-slate-700 hover:bg-slate-50/50 transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-slate-400" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 4v8a1 1 0 001 1h10a1 1 0 001-1V4M2 4l2-2h4l2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
                    문서 선택
                    {selectedDocs.length > 0 && <span className="text-xs text-blue-500 font-semibold bg-blue-50 px-1.5 py-0.5 rounded-full">{selectedDocs.length}</span>}
                  </span>
                  <svg className={`w-4 h-4 text-slate-400 transition-transform ${docsCollapsed ? '' : 'rotate-180'}`} viewBox="0 0 16 16" fill="none"><path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
                </button>
                {!docsCollapsed && (
                  <div className="px-3.5 pb-3 max-h-48 overflow-y-auto border-t border-slate-100">
                    <FolderTree tree={tree} projectName={currentProject} selectable selectedDocs={selectedDocs} onSelectionChange={setSelectedDocs} />
                  </div>
                )}
              </div>

              {/* Context */}
              <div className="glass-card p-4">
                <label className="block text-sm font-semibold text-slate-700 mb-2">추가 컨텍스트</label>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="보고서에 포함할 추가 정보나 지시사항..."
                  rows={3}
                  className="w-full px-3 py-2.5 text-sm input-ring resize-none"
                />
              </div>

              {/* Upload */}
              <div className="glass-card p-4">
                <FilePicker onFilesSelected={handleUpload} loading={uploading} />
                {uploadStatus && <div className="mt-2 text-xs text-slate-500">{uploadStatus}</div>}
              </div>

              {/* Generate button */}
              <button
                onClick={handleGenerate}
                disabled={!selectedTemplate}
                className={`w-full py-3.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  selectedTemplate
                    ? 'btn-primary'
                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                }`}
              >
                작성 시작
              </button>
            </div>

            {/* Right: preview */}
            <div className="flex-1 glass-card-elevated p-5 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 340px)' }}>
              {selectedTemplate && TEMPLATE_PREVIEWS[selectedTemplate] ? (
                <div className="animate-fade-in">
                  <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
                    <span className="text-lg">{currentTemplates.find(t => t.id === selectedTemplate)?.icon}</span>
                    <div>
                      <div className="text-sm font-bold text-slate-700">{currentTemplates.find(t => t.id === selectedTemplate)?.label}</div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">Template Preview</div>
                    </div>
                  </div>

                  {/* Section selector for templates with selectable sections */}
                  {TEMPLATE_SECTIONS[selectedTemplate] && (
                    <div className="mb-4 p-3 bg-slate-50/80 rounded-xl border border-slate-100">
                      <div className="flex items-center justify-between mb-2.5">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">섹션 선택</span>
                        <button
                          onClick={() => {
                            const all = TEMPLATE_SECTIONS[selectedTemplate].map(s => s.id);
                            setSelectedSections(selectedSections.length === all.length ? [] : all);
                          }}
                          className="text-[11px] text-blue-500 hover:text-blue-700 font-medium"
                        >
                          {selectedSections.length === TEMPLATE_SECTIONS[selectedTemplate].length ? '전체 해제' : '전체 선택'}
                        </button>
                      </div>
                      <div className="space-y-1">
                        {TEMPLATE_SECTIONS[selectedTemplate].map((sec) => (
                          <label
                            key={sec.id}
                            className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-all ${
                              selectedSections.includes(sec.id) ? 'bg-blue-50/80 border border-blue-200' : 'hover:bg-white border border-transparent'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={selectedSections.includes(sec.id)}
                              onChange={() => {
                                setSelectedSections(prev =>
                                  prev.includes(sec.id) ? prev.filter(id => id !== sec.id) : [...prev, sec.id]
                                );
                              }}
                              className="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 focus:ring-1"
                            />
                            <span className={`text-sm ${selectedSections.includes(sec.id) ? 'font-semibold text-blue-700' : 'text-slate-600'}`}>
                              {sec.label}
                            </span>
                          </label>
                        ))}
                      </div>
                      {selectedSections.length > 0 && selectedSections.length < TEMPLATE_SECTIONS[selectedTemplate].length && (
                        <div className="mt-2 text-[11px] text-amber-600 bg-amber-50 px-2.5 py-1.5 rounded-md">
                          {TEMPLATE_SECTIONS[selectedTemplate].length}개 중 {selectedSections.length}개 섹션 선택됨
                        </div>
                      )}
                    </div>
                  )}

                  <MarkdownViewer content={TEMPLATE_PREVIEWS[selectedTemplate]} />
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-slate-400">
                  <svg className="w-10 h-10 mb-3 opacity-30" viewBox="0 0 24 24" fill="none"><path d="M9 12h6M9 16h6M13 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" strokeWidth="1.5"/></svg>
                  <span className="text-sm">템플릿을 선택하면 미리보기가 표시됩니다</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ======================== PHASE 2: Generate ======================== */}
      {!isPhase1 && phase2View === 'generate' && (
        <div className="glass-card-elevated p-6 animate-fade-in-up">
          {generating && (
            <GenerationProgress streamingText={streamingText} startTime={genStartTime} onStop={handleStopGenerate} />
          )}
          <div className="max-h-[60vh] overflow-y-auto">
            <MarkdownViewer content={streamingText || result} />
          </div>
          {!generating && result && (
            <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
              <button onClick={() => setPhase2View('refine')} className="px-4 py-2 btn-primary text-sm rounded-lg">수정/보완</button>
              <button onClick={() => setPhase2View('result')} className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">최종 결과로</button>
            </div>
          )}
        </div>
      )}

      {/* ======================== PHASE 2: Refine ======================== */}
      {!isPhase1 && phase2View === 'refine' && (
        <div className="flex gap-4 animate-fade-in-up" style={{ height: 'calc(100vh - 280px)' }}>
          <div className="flex-1 glass-card-elevated p-5 overflow-y-auto">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">현재 보고서</div>
            <MarkdownViewer content={result} />
          </div>
          <div className="w-96 glass-card-elevated p-4 flex flex-col">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">수정 요청</div>
            <ChatWidget messages={chatMessages} onSend={handleRefine} loading={chatLoading} onStop={handleStopChat} placeholder="수정할 내용을 입력하세요..." />
          </div>
        </div>
      )}

      {/* ======================== PHASE 2: Result ======================== */}
      {!isPhase1 && phase2View === 'result' && (
        <div className="glass-card-elevated p-6 animate-fade-in-up">
          <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center gradient-accent text-white text-sm">📄</div>
              <span className="text-sm font-bold text-slate-700">최종 결과</span>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setPhase2View('refine')} className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">수정/보완</button>
              <button onClick={() => downloadAsWord(result, generateFilename(activePage || '보고서', 'docx', currentProject))} className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">Word</button>
              <button onClick={downloadMarkdown} className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">MD</button>
              <button onClick={() => copyRichText(result)} className="px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors">복사</button>
            </div>
          </div>
          <div className="max-h-[60vh] overflow-y-auto">
            <MarkdownViewer content={result} />
          </div>
        </div>
      )}
    </div>
  );
}
