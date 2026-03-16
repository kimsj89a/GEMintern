import{u as Ae,r,a as b,j as e}from"./index-BiN46dNZ.js";import{s as $e,u as J}from"./ws-DjMr0KkP.js";import{F as fe}from"./FolderTree-UQYdYlwz.js";import{F as ge}from"./FilePicker-CYCLpMuS.js";import{C as ve}from"./ChatWidget-B_9Yz5d6.js";import{M as _}from"./MarkdownViewer-B2pPocPe.js";import{c as X,d as O,g as I}from"./clipboard-CFllglB1.js";import{G as Be}from"./GenerationProgress-BrOeySd-.js";function Le(i,u){if(!i||!u||i===u)return u;const g=d=>d.split(/\n{2,}/).map(m=>m.trim()).filter(Boolean),x=g(i),w=g(u),v=d=>d.replace(/\s+/g," ").trim(),W=new Set(x.map(v));return w.map(d=>{const m=v(d);if(W.has(m))return d;if(/^#{1,6}\s/.test(d)){const V=v(d.replace(/^#{1,6}\s+/,""));if(x.some(Y=>v(Y.replace(/^#{1,6}\s+/,""))===V))return d}return`<div class="diff-highlight">

${d}

</div>`}).join(`

`)}const De=[{id:"inv1",label:"1. 투자내용",structure:`## 1. 투자내용
### 1.1 투자개요
### 1.2 투자 구조 및 재원
### 1.3 주요 투자 조건 (Key Terms)
### 1.4 예상사용계획
### 1.5 투자 전/후 주주구성`},{id:"inv2",label:"2. 회사현황",structure:`## 2. 회사현황
### 2.1 회사개요
### 2.2 회사연혁
### 2.3 조직현황
### 2.4 주요 경영진 현황
### 2.5 기존 투자이력
### 2.6 차입금 주주 현황
### 2.7 재무현황`},{id:"inv3",label:"3. 시장분석",structure:`## 3. 시장분석
### 3.1 시장 현황 및 산업 매력도
### 3.2 경쟁 환경 분석
### 3.3 규제 및 정책 환경`},{id:"inv4",label:"4. 사업분석",structure:`## 4. 사업분석
### 4.1 사업개요 (비즈니스 모델)
### 4.2 주요 제품 및 서비스
### 4.3 특별 기술력 검토
### 4.4 경쟁력 대비 차별화
### 4.5 재무실적과 향후 매출 추정`},{id:"inv5",label:"5. 투자 타당성 분석",structure:`## 5. 투자 타당성 분석
### 5.1 Valuation 분석
### 5.2 Value-up 방안
### 5.3 Exit Scenario별 투자수익률`},{id:"inv6",label:"6. 리스크 분석",structure:`## 6. 리스크 분석
### 6.1 산업/사업 리스크
### 6.2 재무/법률 리스크
### 6.3 Exit 리스크`},{id:"inv7",label:"7. 종합의견",structure:`## 7. 종합의견
### 7.1 투자포인트
### 7.2 투자우려요소
### 7.3 종합의견`}],y={investment:De},Oe=[{id:"simple_review",label:"간단 검토",desc:"예비투자심의 Quick Memo",icon:"📋"},{id:"free_summary",label:"자유 요약",desc:"자료 특성 맞춤 자유 구조화",icon:"📝"},{id:"context_based",label:"컨텍스트 기반",desc:"사용자 지시 중심 보고서",icon:"🔍"},{id:"investment",label:"투자 보고서",desc:"투자위원회 심의용",icon:"💰"},{id:"management",label:"경영 분석",desc:"투자 후 경영관리 보고서",icon:"📊"},{id:"term_sheet",label:"Term Sheet",desc:"투자조건 요약서",icon:"📑"},{id:"loi_mou",label:"LOI/MOU",desc:"인수의향서 초안",icon:"🤝"},{id:"im",label:"IM 작성",desc:"Investment Memorandum",icon:"📖"},{id:"teaser",label:"Teaser",desc:"1장짜리 딜 요약",icon:"🎯"},{id:"dd_report",label:"DD 보고서",desc:"실사결과보고서",icon:"🔬"}],We=[{id:"presentation",label:"발표자료",desc:"2-Column 투자 발표 슬라이드",icon:"📊"},{id:"paper_review",label:"논문 발표자료",desc:"논문 구조 자동 인식 슬라이드",icon:"📄"}],je={simple_review:`# 1. 투자 개요
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
# 6. 향후 추진 일정 (표)`,free_summary:`(자유 구조화 요약 모드)

제공된 자료의 특성에 맞게 최적의 구조로 요약합니다.

### 권장 구조 (참고용)
- Executive Summary: 핵심 내용 3~5줄 요약
- 핵심 데이터: 주요 수치/지표 정리 (표 활용)
- 주요 내용: 카테고리별 상세 내용
- 시사점: 데이터에서 도출된 인사이트

※ 위 구조는 예시이며, 자료 특성에 따라 자유롭게 변형됩니다.`,context_based:`(컨텍스트 기반 작성 모드)

사용자가 입력한 지시사항을 중심으로 보고서를 작성합니다.

### 사용 방법
1. "추가 컨텍스트" 란에 원하는 보고서 구조/내용을 상세히 기술
2. 업로드된 자료에서 관련 내용을 자동 추출
3. 지시사항에 맞춰 맞춤형 보고서 생성

※ 자유도가 가장 높은 모드입니다.`,investment:`# 투자심사보고서: [대상기업명]

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

## 7. 종합의견`,management:`# 1. 투자 현황 요약 (표)

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
## 6.3 향후 계획`,term_sheet:`# Term Sheet Summary: [대상회사명]

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

## 협상 포인트 (Negotiation Points) - 표`,loi_mou:`# 인수의향서 (Letter of Intent)

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

서명란`,im:`# 1. Investment Highlights
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
## 6.1~6.3 (성장전략, 자금사용, Exit 시나리오)`,teaser:`# [대상회사명] — Investment Teaser

## Investment Highlights (3대 포인트)

---
## Company Snapshot (표)
## Market Opportunity (시장규모, 성장동력)
## Financial Summary (표: 매출/EBITDA/순이익)
## Proposed Transaction (표: 거래유형/규모/Valuation)

※ 1장짜리 딜 요약 문서`,dd_report:`# 실사결과보고서 (Due Diligence Report)

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
# 6. Recommendations (권고사항)`,presentation:`# 1. Executive Summary
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

※ 2-Column 투자 발표 슬라이드 형태로 생성`,paper_review:`(자동 구조 인식 모드)

업로드된 논문의 실제 섹션 구조를 자동 인식하여 슬라이드를 구성합니다.

### 일반적인 논문 구조
- Abstract → 1~2 슬라이드
- Introduction / Background → 2~3 슬라이드
- Method / Approach → 3~5 슬라이드
- Experiments / Results → 3~5 슬라이드
- Discussion → 1~2 슬라이드
- Conclusion → 1 슬라이드

※ 각 섹션의 내용 분량에 따라 슬라이드 개수가 자동 조절됩니다.`},Ne={phase1:{title:"사전 정보 수집",desc:"투자 대상 기업/자산의 기초 자료를 수집하고 분석합니다.",steps:[{id:1,label:"자료 업로드"},{id:2,label:"자료 분석"},{id:3,label:"자료 Q&A"}]},phase2:{title:"문서 작성",desc:"수집된 자료를 바탕으로 보고서 또는 PPT를 생성합니다.",steps:[]}};function qe(){const{currentProject:i,activePage:u}=Ae(),g=Ne[u]||Ne.phase2,x=u==="phase1",[w,v]=r.useState(1),[W,d]=r.useState({}),[m,V]=r.useState([]),[Y,ye]=r.useState(""),[Z,k]=r.useState(!1),[o,j]=r.useState(""),[F,S]=r.useState(""),[de,xe]=r.useState(!1),[H,ee]=r.useState(""),[we,ke]=r.useState(0),[M,T]=r.useState(""),[C,te]=r.useState([]),[P,G]=r.useState(null),[se,z]=r.useState(null),[A,$]=r.useState(!1),[ae,N]=r.useState([]),[me,f]=r.useState(!1),[E,Se]=r.useState(""),[B,ue]=r.useState(!0),[L,R]=r.useState("choice"),[le,he]=r.useState("report"),[c,re]=r.useState(""),[h,U]=r.useState([]),[ne,Ce]=r.useState(!0),ie=r.useRef(!1),K=r.useRef(!1),D=r.useRef(!1),oe=r.useRef(null),p=r.useRef(null);r.useEffect(()=>{i&&b.getProjectDocs(i).then(t=>d(t.folder_tree||{})).catch(()=>d({}))},[i]);const pe=async t=>{if(i){xe(!0),ee("");try{const s=await b.uploadFiles(i,t),a=Object.keys(s.parsed_texts||{}).length,l=s.parse_errors?.length>0?` (${s.parse_errors.length}개 파싱 실패)`:"";ee(`${a}개 파일 업로드 완료${l}`);const n=await b.getProjectDocs(i);d(n.folder_tree||{})}catch{ee("업로드 실패")}xe(!1)}},_e=async()=>{if(i){$(!0),T(""),te([]),G(null),z(null),v(2),ie.current=!1;try{const{task_id:t}=await b.startAnalysis({task_type:"material_summary_batch",kwargs:{project_name:i,selected_docs:m}}),s=async()=>{if(ie.current)return;const a=await b.getTaskStatus(t);if(a.status==="complete"){try{const l=JSON.parse(a.result||"[]");te(l),l.length>0&&z(0);const n=l.map(q=>`# 📄 ${q.filename}

${q.result}`).join(`

---

`);T(n)}catch{T(a.result||"")}G(null),$(!1)}else a.status==="error"?(T(`오류: ${a.error}`),$(!1)):(a.batch_progress&&(G({completed:a.batch_progress.completed,total:a.batch_progress.total}),a.batch_progress.partial_results?.length&&(te(a.batch_progress.partial_results),z(l=>l===null&&a.batch_progress.partial_results.length>0?0:l))),setTimeout(s,2e3))};s()}catch(t){T(`오류: ${t.message}`),$(!1)}}},Me=()=>{if(ie.current=!0,$(!1),G(null),C.length>0){const t=C.map(s=>`# 📄 ${s.filename}

${s.result}`).join(`

---

`);T(t)}},Te=async t=>{N(s=>[...s,{role:"user",content:t}]),f(!0),D.current=!1;try{const{task_id:s}=await b.startQa({project_name:i,question:t,selected_docs:m.length>0?m:void 0}),a=async()=>{if(D.current)return;const l=await b.getTaskStatus(s);l.status==="complete"?(N(n=>[...n,{role:"assistant",content:l.result||""}]),f(!1)):l.status==="error"?(N(n=>[...n,{role:"assistant",content:`오류: ${l.error}`}]),f(!1)):setTimeout(a,1e3)};a()}catch(s){N(a=>[...a,{role:"assistant",content:`오류: ${s.message}`}]),f(!1)}},be=()=>{D.current=!0,f(!1)},Pe=async()=>{if(!i||!c)return;k(!0),S(""),j(""),R("generate"),ke(Date.now()),K.current=!1;const t=c==="im"?"chained":"single",s=y[c];let a="";s&&h.length>0&&h.length<s.length&&(a=`# 투자심사보고서: [대상기업명]

`+s.filter(n=>h.includes(n.id)).map(n=>n.structure).join(`

`));try{const{task_id:l}=await b.startGenerate({project_name:i,template_option:c,thinking_level:"MEDIUM",file_context:"",inputs:{selected_docs:m,...a?{structure_text:a}:{}},mode:t});oe.current=l,$e(l,n=>{if(K.current){J(l);return}n.type==="chunk"&&n.data?S(q=>q+n.data):n.type==="complete"?(j(n.result||""),S(""),k(!1),J(l)):n.type==="error"&&(j(`오류: ${n.error}`),S(""),k(!1),J(l))}),p.current=setInterval(async()=>{if(K.current){p.current&&clearInterval(p.current);return}const n=await b.getTaskStatus(l);n.status==="complete"&&!o?(p.current&&clearInterval(p.current),j(n.result||""),S(""),k(!1)):n.status==="error"&&!o&&(p.current&&clearInterval(p.current),j(`오류: ${n.error}`),S(""),k(!1))},3e3),setTimeout(()=>{p.current&&clearInterval(p.current)},6e5)}catch(l){j(`오류: ${l.message}`),k(!1)}},Ee=()=>{K.current=!0,oe.current&&J(oe.current),p.current&&clearInterval(p.current),F&&j(F),S(""),k(!1)},Re=async t=>{N(s=>[...s,{role:"user",content:t}]),f(!0),D.current=!1,Se(o),ue(!0);try{const{task_id:s}=await b.startAnalysis({task_type:"refine",kwargs:{current_text:o,chat_history:ae,refine_query:t,additional_file_context:""}}),a=async()=>{if(D.current)return;const l=await b.getTaskStatus(s);l.status==="complete"?(j(l.result||""),N(n=>[...n,{role:"assistant",content:"보고서가 수정되었습니다."}]),f(!1)):l.status==="error"?(N(n=>[...n,{role:"assistant",content:`오류: ${l.error}`}]),f(!1)):setTimeout(a,1e3)};a()}catch(s){N(a=>[...a,{role:"assistant",content:`오류: ${s.message}`}]),f(!1)}},Q=()=>{const t=o||M,s=new Blob([t],{type:"text/markdown"}),a=URL.createObjectURL(s),l=document.createElement("a");l.href=a,l.download=I(u||"자료분석","md",i),l.click(),URL.revokeObjectURL(a)},Ie=r.useMemo(()=>!B||!E||E===o?o:Le(E,o),[o,E,B]);if(!i)return e.jsxs("div",{className:"p-8 max-w-5xl mx-auto",children:[e.jsx("h1",{className:"text-xl font-bold text-slate-800 mb-2",children:g.title}),e.jsxs("div",{className:"flex flex-col items-center py-16 text-slate-400",children:[e.jsx("svg",{className:"w-12 h-12 mb-3 opacity-30",viewBox:"0 0 24 24",fill:"none",children:e.jsx("path",{d:"M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z",stroke:"currentColor",strokeWidth:"1.5"})}),e.jsx("span",{className:"text-sm",children:"프로젝트를 먼저 선택하세요."})]})]});const ce=le==="report"?Oe:We;return e.jsxs("div",{className:"p-8 max-w-6xl mx-auto",children:[e.jsxs("div",{className:"mb-5 animate-fade-in",children:[e.jsx("h1",{className:"text-xl font-bold text-slate-800 tracking-tight",children:g.title}),e.jsx("p",{className:"text-sm text-slate-500 mt-0.5",children:g.desc})]}),x&&e.jsx("div",{className:"flex items-center gap-1.5 mb-6",children:g.steps.map((t,s)=>e.jsxs("div",{className:"flex items-center",children:[e.jsxs("button",{onClick:()=>!Z&&!A&&v(t.id),className:`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 ${w===t.id?"btn-primary shadow-sm":w>t.id?"bg-blue-50 text-blue-600":"bg-slate-100 text-slate-400"}`,children:[t.id,". ",t.label]}),s<g.steps.length-1&&e.jsx("svg",{className:"w-4 h-4 mx-1 text-slate-300",viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M6 4l4 4-4 4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})})]},t.id))}),x&&w===1&&e.jsx("div",{className:"space-y-4 animate-fade-in-up",children:e.jsxs("div",{className:"flex gap-4",children:[e.jsxs("div",{className:"w-64 shrink-0 glass-card p-3 max-h-80 overflow-y-auto",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2",children:"프로젝트 문서"}),e.jsx(fe,{tree:W,projectName:i,selectable:!0,selectedDocs:m,onSelectionChange:V})]}),e.jsxs("div",{className:"flex-1 space-y-4",children:[e.jsxs("div",{className:"glass-card p-4",children:[e.jsx("label",{className:"block text-sm font-semibold text-slate-700 mb-2",children:"추가 자료 업로드"}),e.jsx(ge,{onFilesSelected:pe,loading:de}),H&&e.jsx("div",{className:"mt-2 text-sm text-slate-500",children:H})]}),e.jsx("button",{onClick:_e,className:"w-full py-3 btn-primary rounded-xl text-sm",children:"자료 분석 시작"})]})]})}),x&&w===2&&e.jsxs("div",{className:"animate-fade-in-up space-y-3",children:[A&&e.jsxs("div",{className:"glass-card p-4 flex items-center gap-3",children:[e.jsx("div",{className:"w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"}),e.jsx("span",{className:"text-sm text-slate-500",children:P?`분석 중... (${P.completed}/${P.total}건 완료)`:"분석 준비 중..."}),e.jsx("button",{onClick:Me,className:"px-3 py-1 bg-red-500 text-white text-xs font-semibold rounded-lg hover:bg-red-600 transition-all",children:"중지"})]}),C.length>0&&e.jsx("div",{className:"space-y-2",children:C.map((t,s)=>e.jsxs("div",{className:"glass-card-elevated overflow-hidden",children:[e.jsxs("button",{onClick:()=>z(se===s?null:s),className:"w-full flex items-center justify-between p-4 text-left hover:bg-slate-50/50 transition-colors",children:[e.jsxs("div",{className:"flex items-center gap-2.5",children:[e.jsx("span",{className:"text-base",children:"📄"}),e.jsx("span",{className:"text-sm font-semibold text-slate-700",children:t.filename}),A&&s===C.length-1&&P&&P.completed<P.total&&e.jsx("span",{className:"text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full font-medium",children:"방금 완료"})]}),e.jsx("svg",{className:`w-4 h-4 text-slate-400 transition-transform ${se===s?"rotate-180":""}`,viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M4 6l4 4 4-4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})})]}),se===s&&e.jsxs("div",{className:"px-5 pb-5 border-t border-slate-100",children:[e.jsx("div",{className:"max-h-[50vh] overflow-y-auto pt-4",children:e.jsx(_,{content:t.result})}),e.jsxs("div",{className:"flex gap-2 mt-3 pt-3 border-t border-slate-100",children:[e.jsx("button",{onClick:()=>X(t.result),className:"px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors",children:"서식 복사"}),e.jsx("button",{onClick:()=>O(t.result,I(t.filename,"docx",i)),className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors",children:"Word"})]})]})]},s))}),C.length===0&&M&&!A&&e.jsx("div",{className:"glass-card-elevated p-6",children:e.jsx("div",{className:"max-h-[60vh] overflow-y-auto",children:e.jsx(_,{content:M})})}),!A&&(C.length>0||M)&&e.jsxs("div",{className:"flex gap-2 pt-2",children:[e.jsx("button",{onClick:()=>v(3),className:"px-4 py-2 btn-primary text-sm rounded-lg",children:"자료 Q&A"}),e.jsx("button",{onClick:()=>O(M,I("자료분석","docx",i)),className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"전체 Word 저장"}),e.jsx("button",{onClick:Q,className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"전체 MD 저장"})]})]}),x&&w===3&&e.jsxs("div",{className:"flex gap-4 animate-fade-in-up",style:{height:"calc(100vh - 280px)"},children:[e.jsxs("div",{className:"flex-1 glass-card-elevated p-5 overflow-y-auto",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:"분석 결과"}),e.jsx(_,{content:M})]}),e.jsxs("div",{className:"w-96 glass-card-elevated p-4 flex flex-col",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:"자료 기반 Q&A"}),e.jsx(ve,{messages:ae,onSend:Te,loading:me,onStop:be,placeholder:"자료에 대해 질문하세요..."})]})]}),!x&&L==="choice"&&e.jsx("div",{className:"flex items-center justify-center animate-fade-in-up",style:{minHeight:"calc(100vh - 280px)"},children:e.jsxs("div",{className:"flex gap-6",children:[e.jsxs("button",{onClick:()=>{he("report"),re(""),R("templates")},className:"group w-72 glass-card-elevated p-8 flex flex-col items-center gap-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden",children:[e.jsx("div",{className:"absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-blue-500 to-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity"}),e.jsx("div",{className:"w-16 h-16 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-300",style:{background:"linear-gradient(135deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))"},children:"📄"}),e.jsxs("div",{children:[e.jsx("div",{className:"text-lg font-bold text-slate-800",children:"보고서 작성"}),e.jsx("div",{className:"text-sm text-slate-500 mt-1",children:"투심보고서, IM, Term Sheet 등"}),e.jsx("div",{className:"text-xs text-blue-500 font-semibold mt-2",children:"10종 템플릿"})]})]}),e.jsxs("button",{onClick:()=>{he("ppt"),re(""),R("templates")},className:"group w-72 glass-card-elevated p-8 flex flex-col items-center gap-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden",children:[e.jsx("div",{className:"absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-violet-500 to-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"}),e.jsx("div",{className:"w-16 h-16 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-300",style:{background:"linear-gradient(135deg, rgba(139,92,246,0.1), rgba(59,130,246,0.1))"},children:"📊"}),e.jsxs("div",{children:[e.jsx("div",{className:"text-lg font-bold text-slate-800",children:"PPT 작성"}),e.jsx("div",{className:"text-sm text-slate-500 mt-1",children:"투자 발표, 논문 발표"}),e.jsx("div",{className:"text-xs text-violet-500 font-semibold mt-2",children:"2종 템플릿"})]})]})]})}),!x&&L==="templates"&&e.jsxs("div",{className:"animate-fade-in-up",children:[e.jsxs("button",{onClick:()=>R("choice"),className:"mb-4 flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all",children:[e.jsx("svg",{className:"w-4 h-4",viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M10 4L6 8l4 4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})}),"돌아가기"]}),e.jsxs("div",{className:"flex gap-5",style:{minHeight:"calc(100vh - 340px)"},children:[e.jsxs("div",{className:"w-[480px] shrink-0 space-y-4 overflow-y-auto pr-1",style:{maxHeight:"calc(100vh - 340px)"},children:[e.jsxs("div",{className:"glass-card p-4",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:le==="report"?"보고서 템플릿":"PPT 템플릿"}),e.jsx("div",{className:`grid gap-2 stagger-children ${le==="report"?"grid-cols-2":"grid-cols-1"}`,children:ce.map(t=>e.jsxs("button",{onClick:()=>{re(t.id);const s=y[t.id];U(s?s.map(a=>a.id):[])},className:`text-left p-3 rounded-xl border transition-all duration-200 group ${c===t.id?"border-blue-300 bg-blue-50/70 shadow-sm":"border-slate-100 hover:border-slate-200 hover:bg-slate-50/50"}`,children:[e.jsxs("div",{className:"flex items-center gap-2 mb-0.5",children:[e.jsx("span",{className:"text-base group-hover:scale-110 transition-transform",children:t.icon}),e.jsx("span",{className:`text-sm font-semibold ${c===t.id?"text-blue-700":"text-slate-700"}`,children:t.label})]}),e.jsx("div",{className:"text-xs text-slate-400 pl-7",children:t.desc})]},t.id))})]}),e.jsxs("div",{className:"glass-card overflow-hidden",children:[e.jsxs("button",{onClick:()=>Ce(!ne),className:"w-full flex items-center justify-between p-3.5 text-sm font-semibold text-slate-700 hover:bg-slate-50/50 transition-colors",children:[e.jsxs("span",{className:"flex items-center gap-2",children:[e.jsx("svg",{className:"w-4 h-4 text-slate-400",viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M2 4h12M2 4v8a1 1 0 001 1h10a1 1 0 001-1V4M2 4l2-2h4l2 2",stroke:"currentColor",strokeWidth:"1.2",strokeLinecap:"round"})}),"문서 선택",m.length>0&&e.jsx("span",{className:"text-xs text-blue-500 font-semibold bg-blue-50 px-1.5 py-0.5 rounded-full",children:m.length})]}),e.jsx("svg",{className:`w-4 h-4 text-slate-400 transition-transform ${ne?"":"rotate-180"}`,viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M4 6l4 4 4-4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})})]}),!ne&&e.jsx("div",{className:"px-3.5 pb-3 max-h-48 overflow-y-auto border-t border-slate-100",children:e.jsx(fe,{tree:W,projectName:i,selectable:!0,selectedDocs:m,onSelectionChange:V})})]}),e.jsxs("div",{className:"glass-card p-4",children:[e.jsx("label",{className:"block text-sm font-semibold text-slate-700 mb-2",children:"추가 컨텍스트"}),e.jsx("textarea",{value:Y,onChange:t=>ye(t.target.value),placeholder:"보고서에 포함할 추가 정보나 지시사항...",rows:3,className:"w-full px-3 py-2.5 text-sm input-ring resize-none"})]}),e.jsxs("div",{className:"glass-card p-4",children:[e.jsx(ge,{onFilesSelected:pe,loading:de}),H&&e.jsx("div",{className:"mt-2 text-xs text-slate-500",children:H})]}),e.jsx("button",{onClick:Pe,disabled:!c,className:`w-full py-3.5 rounded-xl text-sm font-semibold transition-all duration-200 ${c?"btn-primary":"bg-slate-100 text-slate-400 cursor-not-allowed"}`,children:"작성 시작"})]}),e.jsx("div",{className:"flex-1 glass-card-elevated p-5 overflow-y-auto",style:{maxHeight:"calc(100vh - 340px)"},children:c&&je[c]?e.jsxs("div",{className:"animate-fade-in",children:[e.jsxs("div",{className:"flex items-center gap-2 mb-4 pb-3 border-b border-slate-100",children:[e.jsx("span",{className:"text-lg",children:ce.find(t=>t.id===c)?.icon}),e.jsxs("div",{children:[e.jsx("div",{className:"text-sm font-bold text-slate-700",children:ce.find(t=>t.id===c)?.label}),e.jsx("div",{className:"text-[10px] text-slate-400 uppercase tracking-wider font-medium",children:"Template Preview"})]})]}),y[c]&&e.jsxs("div",{className:"mb-4 p-3 bg-slate-50/80 rounded-xl border border-slate-100",children:[e.jsxs("div",{className:"flex items-center justify-between mb-2.5",children:[e.jsx("span",{className:"text-xs font-bold text-slate-500 uppercase tracking-wider",children:"섹션 선택"}),e.jsx("button",{onClick:()=>{const t=y[c].map(s=>s.id);U(h.length===t.length?[]:t)},className:"text-[11px] text-blue-500 hover:text-blue-700 font-medium",children:h.length===y[c].length?"전체 해제":"전체 선택"})]}),e.jsx("div",{className:"space-y-1",children:y[c].map(t=>e.jsxs("label",{className:`flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-all ${h.includes(t.id)?"bg-blue-50/80 border border-blue-200":"hover:bg-white border border-transparent"}`,children:[e.jsx("input",{type:"checkbox",checked:h.includes(t.id),onChange:()=>{U(s=>s.includes(t.id)?s.filter(a=>a!==t.id):[...s,t.id])},className:"w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 focus:ring-1"}),e.jsx("span",{className:`text-sm ${h.includes(t.id)?"font-semibold text-blue-700":"text-slate-600"}`,children:t.label})]},t.id))}),h.length>0&&h.length<y[c].length&&e.jsxs("div",{className:"mt-2 text-[11px] text-amber-600 bg-amber-50 px-2.5 py-1.5 rounded-md",children:[y[c].length,"개 중 ",h.length,"개 섹션 선택됨"]})]}),e.jsx(_,{content:je[c]})]}):e.jsxs("div",{className:"flex flex-col items-center justify-center h-full text-slate-400",children:[e.jsxs("svg",{className:"w-10 h-10 mb-3 opacity-30",viewBox:"0 0 24 24",fill:"none",children:[e.jsx("path",{d:"M9 12h6M9 16h6M13 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V11",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"}),e.jsx("path",{d:"M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z",stroke:"currentColor",strokeWidth:"1.5"})]}),e.jsx("span",{className:"text-sm",children:"템플릿을 선택하면 미리보기가 표시됩니다"})]})})]})]}),!x&&L==="generate"&&e.jsxs("div",{className:"glass-card-elevated p-6 animate-fade-in-up",children:[Z&&e.jsx(Be,{streamingText:F,startTime:we,onStop:Ee}),e.jsx("div",{className:"max-h-[60vh] overflow-y-auto",children:e.jsx(_,{content:F||o})}),!Z&&o&&e.jsxs("div",{className:"flex gap-2 mt-4 pt-4 border-t border-slate-100",children:[e.jsx("button",{onClick:()=>R("refine"),className:"px-4 py-2 btn-primary text-sm rounded-lg",children:"수정/보완"}),e.jsx("button",{onClick:()=>X(o),className:"px-4 py-2 text-sm text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors",children:"서식 복사"}),e.jsx("button",{onClick:()=>O(o,I(u||"보고서","docx",i)),className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"Word"}),e.jsx("button",{onClick:Q,className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"MD"})]})]}),!x&&L==="refine"&&e.jsxs("div",{className:"flex gap-4 animate-fade-in-up",style:{height:"calc(100vh - 280px)"},children:[e.jsxs("div",{className:"flex-1 glass-card-elevated flex flex-col overflow-hidden",children:[e.jsxs("div",{className:"flex items-center justify-between px-5 pt-4 pb-2",children:[e.jsxs("div",{className:"flex items-center gap-2",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider",children:"현재 보고서"}),E&&E!==o&&e.jsx("button",{onClick:()=>ue(!B),className:`px-2 py-0.5 text-[10px] font-medium rounded-full transition-colors ${B?"bg-amber-100 text-amber-700 border border-amber-200":"bg-slate-100 text-slate-500 border border-slate-200"}`,children:B?"변경 표시 ON":"변경 표시 OFF"})]}),e.jsxs("div",{className:"flex gap-1.5",children:[e.jsx("button",{onClick:()=>X(o),className:"px-2.5 py-1 text-[11px] font-medium text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors",children:"서식복사"}),e.jsx("button",{onClick:()=>O(o,I(u||"보고서","docx",i)),className:"px-2.5 py-1 text-[11px] font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors",children:"Word"}),e.jsx("button",{onClick:Q,className:"px-2.5 py-1 text-[11px] font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors",children:"MD"})]})]}),e.jsx("div",{className:"flex-1 px-5 pb-5 overflow-y-auto",children:e.jsx(_,{content:Ie})})]}),e.jsxs("div",{className:"w-96 glass-card-elevated p-4 flex flex-col",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:"수정 요청"}),e.jsx(ve,{messages:ae,onSend:Re,loading:me,onStop:be,placeholder:"수정할 내용을 입력하세요..."})]})]}),!x&&L==="result"&&e.jsxs("div",{className:"glass-card-elevated p-6 animate-fade-in-up",children:[e.jsxs("div",{className:"flex items-center justify-between mb-4 pb-4 border-b border-slate-100",children:[e.jsxs("div",{className:"flex items-center gap-2",children:[e.jsx("div",{className:"w-8 h-8 rounded-lg flex items-center justify-center gradient-accent text-white text-sm",children:"📄"}),e.jsx("span",{className:"text-sm font-bold text-slate-700",children:"최종 결과"})]}),e.jsxs("div",{className:"flex gap-2",children:[e.jsx("button",{onClick:()=>R("refine"),className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"수정/보완"}),e.jsx("button",{onClick:()=>O(o,I(u||"보고서","docx",i)),className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"Word"}),e.jsx("button",{onClick:Q,className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"MD"}),e.jsx("button",{onClick:()=>X(o),className:"px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors",children:"복사"})]})]}),e.jsx("div",{className:"max-h-[60vh] overflow-y-auto",children:e.jsx(_,{content:o})})]})]})}export{qe as default};
