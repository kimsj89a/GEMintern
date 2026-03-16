import{u as Ke,r,a as x,j as e}from"./index-DIg8JHVT.js";import{s as qe,u as ae}from"./ws-Bm0gYk8s.js";import{F as Te}from"./FolderTree-nnm7EdhC.js";import{F as Me}from"./FilePicker-CJ6jB7XI.js";import{C as Re}from"./ChatWidget-DHmeeNu6.js";import{M as w}from"./MarkdownViewer-Dd8IYv35.js";import{c as z,d as U,g as A}from"./clipboard-CQD9uCWL.js";import{G as Je}from"./GenerationProgress-bzeyRlnG.js";function Xe(n,h){if(!n||!h||n===h)return h;const g=d=>d.split(/\n{2,}/).map(u=>u.trim()).filter(Boolean),m=g(n),S=g(h),v=d=>d.replace(/\s+/g," ").trim(),Q=new Set(m.map(v));return S.map(d=>{const u=v(d);if(Q.has(u))return d;if(/^#{1,6}\s/.test(d)){const K=v(d.replace(/^#{1,6}\s+/,""));if(m.some(re=>v(re.replace(/^#{1,6}\s+/,""))===K))return d}return`<div class="diff-highlight">

${d}

</div>`}).join(`

`)}const Ye=[{id:"inv1",label:"1. 투자내용",structure:`## 1. 투자내용
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
### 7.3 종합의견`}],k={investment:Ye},Ze=[{id:"simple_review",label:"간단 검토",desc:"예비투자심의 Quick Memo",icon:"📋"},{id:"free_summary",label:"자유 요약",desc:"자료 특성 맞춤 자유 구조화",icon:"📝"},{id:"context_based",label:"컨텍스트 기반",desc:"사용자 지시 중심 보고서",icon:"🔍"},{id:"investment",label:"투자 보고서",desc:"투자위원회 심의용",icon:"💰"},{id:"management",label:"경영 분석",desc:"투자 후 경영관리 보고서",icon:"📊"},{id:"term_sheet",label:"Term Sheet",desc:"투자조건 요약서",icon:"📑"},{id:"loi_mou",label:"LOI/MOU",desc:"인수의향서 초안",icon:"🤝"},{id:"im",label:"IM 작성",desc:"Investment Memorandum",icon:"📖"},{id:"teaser",label:"Teaser",desc:"1장짜리 딜 요약",icon:"🎯"},{id:"dd_report",label:"DD 보고서",desc:"실사결과보고서",icon:"🔬"}],et=[{id:"presentation",label:"발표자료",desc:"2-Column 투자 발표 슬라이드",icon:"📊"},{id:"paper_review",label:"논문 발표자료",desc:"논문 구조 자동 인식 슬라이드",icon:"📄"}],Pe={simple_review:`# 1. 투자 개요
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

※ 각 섹션의 내용 분량에 따라 슬라이드 개수가 자동 조절됩니다.`},Ee={phase1:{title:"사전 정보 수집",desc:"투자 대상 기업/자산의 기초 자료를 수집하고 분석합니다.",steps:[{id:1,label:"자료 업로드"},{id:2,label:"자료 분석"},{id:3,label:"자료 Q&A"}]},phase2:{title:"문서 작성",desc:"수집된 자료를 바탕으로 보고서 또는 PPT를 생성합니다.",steps:[]}};function ct(){const{currentProject:n,activePage:h}=Ke(),g=Ee[h]||Ee.phase2,m=h==="phase1",[S,v]=r.useState(1),[Q,d]=r.useState({}),[u,K]=r.useState([]),[re,$e]=r.useState(""),[le,C]=r.useState(!1),[i,j]=r.useState(""),[q,_]=r.useState(""),[ge,ve]=r.useState(!1),[J,ne]=r.useState(""),[Ie,Ae]=r.useState(0),[R,P]=r.useState(""),[T,oe]=r.useState([]),[E,X]=r.useState(null),[ie,Y]=r.useState(null),[B,D]=r.useState(!1),[ce,N]=r.useState([]),[je,f]=r.useState(!1),[$,Be]=r.useState(""),[L,Ne]=r.useState(!0),[W,I]=r.useState("choice"),[de,ye]=r.useState("report"),[c,xe]=r.useState(""),[p,Z]=r.useState([]),[me,De]=r.useState(!0),[M,we]=r.useState(""),[y,O]=r.useState(""),[F,V]=r.useState(!1),[H,ue]=r.useState(!1),[ke,Le]=r.useState([]),he=r.useRef(!1),pe=r.useRef(!1),ee=r.useRef(!1),G=r.useRef(!1),be=r.useRef(null),b=r.useRef(null);r.useEffect(()=>{n&&x.getProjectDocs(n).then(t=>d(t.folder_tree||{})).catch(()=>d({}))},[n]);const Se=async t=>{if(n){ve(!0),ne("");try{const s=await x.uploadFiles(n,t),a=Object.keys(s.parsed_texts||{}).length,l=s.parse_errors?.length>0?` (${s.parse_errors.length}개 파싱 실패)`:"";ne(`${a}개 파일 업로드 완료${l}`);const o=await x.getProjectDocs(n);d(o.folder_tree||{})}catch{ne("업로드 실패")}ve(!1)}},Ce=async()=>{if(!(!n||!M.trim())){V(!0),O(""),ue(!1),pe.current=!1;try{const{task_id:t}=await x.startAnalysis({task_type:"web_research",kwargs:{query:M.trim()}}),s=async()=>{if(pe.current)return;const a=await x.getTaskStatus(t);a.status==="complete"?(O(a.result||""),V(!1)):a.status==="error"?(O(`오류: ${a.error}`),V(!1)):setTimeout(s,1500)};s()}catch(t){O(`오류: ${t.message}`),V(!1)}}},We=async()=>{if(!n||!y||H)return;const t=`웹리서치_${M.trim().slice(0,30).replace(/[/\\?%*:|"<>]/g,"_")}`;try{await x.saveResearch({project_name:n,doc_name:t,content:y}),ue(!0),Le(a=>[...a,{query:M,result:y,saved:!0}]);const s=await x.getProjectDocs(n);d(s.folder_tree||{})}catch(s){alert(`저장 실패: ${s.message}`)}},Oe=()=>{pe.current=!0,V(!1)},Fe=async()=>{if(n){D(!0),P(""),oe([]),X(null),Y(null),v(2),he.current=!1;try{const{task_id:t}=await x.startAnalysis({task_type:"material_summary_batch",kwargs:{project_name:n,selected_docs:u}}),s=async()=>{if(he.current)return;const a=await x.getTaskStatus(t);if(a.status==="complete"){try{const l=JSON.parse(a.result||"[]");oe(l),l.length>0&&Y(0);const o=l.map(se=>`# 📄 ${se.filename}

${se.result}`).join(`

---

`);P(o)}catch{P(a.result||"")}X(null),D(!1)}else a.status==="error"?(P(`오류: ${a.error}`),D(!1)):(a.batch_progress&&(X({completed:a.batch_progress.completed,total:a.batch_progress.total}),a.batch_progress.partial_results?.length&&(oe(a.batch_progress.partial_results),Y(l=>l===null&&a.batch_progress.partial_results.length>0?0:l))),setTimeout(s,2e3))};s()}catch(t){P(`오류: ${t.message}`),D(!1)}}},Ve=()=>{if(he.current=!0,D(!1),X(null),T.length>0){const t=T.map(s=>`# 📄 ${s.filename}

${s.result}`).join(`

---

`);P(t)}},He=async t=>{N(s=>[...s,{role:"user",content:t}]),f(!0),G.current=!1;try{const{task_id:s}=await x.startQa({project_name:n,question:t,selected_docs:u.length>0?u:void 0}),a=async()=>{if(G.current)return;const l=await x.getTaskStatus(s);l.status==="complete"?(N(o=>[...o,{role:"assistant",content:l.result||""}]),f(!1)):l.status==="error"?(N(o=>[...o,{role:"assistant",content:`오류: ${l.error}`}]),f(!1)):setTimeout(a,1e3)};a()}catch(s){N(a=>[...a,{role:"assistant",content:`오류: ${s.message}`}]),f(!1)}},_e=()=>{G.current=!0,f(!1)},Ge=async()=>{if(!n||!c)return;C(!0),_(""),j(""),I("generate"),Ae(Date.now()),ee.current=!1;const t=c==="im"?"chained":"single",s=k[c];let a="";s&&p.length>0&&p.length<s.length&&(a=`# 투자심사보고서: [대상기업명]

`+s.filter(o=>p.includes(o.id)).map(o=>o.structure).join(`

`));try{const{task_id:l}=await x.startGenerate({project_name:n,template_option:c,thinking_level:"MEDIUM",file_context:"",inputs:{selected_docs:u,...a?{structure_text:a}:{}},mode:t});be.current=l,qe(l,o=>{if(ee.current){ae(l);return}o.type==="chunk"&&o.data?_(se=>se+o.data):o.type==="complete"?(j(o.result||""),_(""),C(!1),ae(l)):o.type==="error"&&(j(`오류: ${o.error}`),_(""),C(!1),ae(l))}),b.current=setInterval(async()=>{if(ee.current){b.current&&clearInterval(b.current);return}const o=await x.getTaskStatus(l);o.status==="complete"&&!i?(b.current&&clearInterval(b.current),j(o.result||""),_(""),C(!1)):o.status==="error"&&!i&&(b.current&&clearInterval(b.current),j(`오류: ${o.error}`),_(""),C(!1))},3e3),setTimeout(()=>{b.current&&clearInterval(b.current)},6e5)}catch(l){j(`오류: ${l.message}`),C(!1)}},ze=()=>{ee.current=!0,be.current&&ae(be.current),b.current&&clearInterval(b.current),q&&j(q),_(""),C(!1)},Ue=async t=>{N(s=>[...s,{role:"user",content:t}]),f(!0),G.current=!1,Be(i),Ne(!0);try{const{task_id:s}=await x.startAnalysis({task_type:"refine",kwargs:{current_text:i,chat_history:ce,refine_query:t,additional_file_context:""}}),a=async()=>{if(G.current)return;const l=await x.getTaskStatus(s);l.status==="complete"?(j(l.result||""),N(o=>[...o,{role:"assistant",content:"보고서가 수정되었습니다."}]),f(!1)):l.status==="error"?(N(o=>[...o,{role:"assistant",content:`오류: ${l.error}`}]),f(!1)):setTimeout(a,1e3)};a()}catch(s){N(a=>[...a,{role:"assistant",content:`오류: ${s.message}`}]),f(!1)}},te=()=>{const t=i||R,s=new Blob([t],{type:"text/markdown"}),a=URL.createObjectURL(s),l=document.createElement("a");l.href=a,l.download=A(h||"자료분석","md",n),l.click(),URL.revokeObjectURL(a)},Qe=r.useMemo(()=>!L||!$||$===i?i:Xe($,i),[i,$,L]);if(!n)return e.jsxs("div",{className:"p-8 max-w-5xl mx-auto",children:[e.jsx("h1",{className:"text-xl font-bold text-slate-800 mb-2",children:g.title}),e.jsxs("div",{className:"flex flex-col items-center py-16 text-slate-400",children:[e.jsx("svg",{className:"w-12 h-12 mb-3 opacity-30",viewBox:"0 0 24 24",fill:"none",children:e.jsx("path",{d:"M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z",stroke:"currentColor",strokeWidth:"1.5"})}),e.jsx("span",{className:"text-sm",children:"프로젝트를 먼저 선택하세요."})]})]});const fe=de==="report"?Ze:et;return e.jsxs("div",{className:"p-8 max-w-6xl mx-auto",children:[e.jsxs("div",{className:"mb-5 animate-fade-in",children:[e.jsx("h1",{className:"text-xl font-bold text-slate-800 tracking-tight",children:g.title}),e.jsx("p",{className:"text-sm text-slate-500 mt-0.5",children:g.desc})]}),m&&e.jsx("div",{className:"flex items-center gap-1.5 mb-6",children:g.steps.map((t,s)=>e.jsxs("div",{className:"flex items-center",children:[e.jsxs("button",{onClick:()=>!le&&!B&&v(t.id),className:`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 ${S===t.id?"btn-primary shadow-sm":S>t.id?"bg-blue-50 text-blue-600":"bg-slate-100 text-slate-400"}`,children:[t.id,". ",t.label]}),s<g.steps.length-1&&e.jsx("svg",{className:"w-4 h-4 mx-1 text-slate-300",viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M6 4l4 4-4 4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})})]},t.id))}),m&&S===1&&e.jsx("div",{className:"space-y-4 animate-fade-in-up",children:e.jsxs("div",{className:"flex gap-4",children:[e.jsxs("div",{className:"w-64 shrink-0 glass-card p-3 max-h-[calc(100vh-320px)] overflow-y-auto",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2",children:"프로젝트 문서"}),e.jsx(Te,{tree:Q,projectName:n,selectable:!0,selectedDocs:u,onSelectionChange:K})]}),e.jsxs("div",{className:"flex-1 space-y-4",children:[e.jsxs("div",{className:"glass-card p-4",children:[e.jsx("label",{className:"block text-sm font-semibold text-slate-700 mb-2",children:"추가 자료 업로드"}),e.jsx(Me,{onFilesSelected:Se,loading:ge}),J&&e.jsx("div",{className:"mt-2 text-sm text-slate-500",children:J})]}),e.jsxs("div",{className:"glass-card p-4",children:[e.jsxs("label",{className:"block text-sm font-semibold text-slate-700 mb-2",children:["웹 리서치",e.jsx("span",{className:"ml-2 text-[10px] font-medium text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded-full",children:"AI 검색"})]}),e.jsxs("div",{className:"flex gap-2",children:[e.jsx("input",{type:"text",value:M,onChange:t=>we(t.target.value),onKeyDown:t=>t.key==="Enter"&&!F&&Ce(),placeholder:"검색할 주제를 입력하세요 (예: 반도체 시장 전망 2026)",className:"flex-1 px-3 py-2 text-sm input-ring",disabled:F}),F?e.jsx("button",{onClick:Oe,className:"px-4 py-2 bg-red-500 text-white text-sm font-semibold rounded-lg hover:bg-red-600 transition-all shrink-0",children:"중지"}):e.jsx("button",{onClick:Ce,disabled:!M.trim(),className:`px-4 py-2 text-sm font-semibold rounded-lg shrink-0 transition-all ${M.trim()?"btn-primary":"bg-slate-100 text-slate-400 cursor-not-allowed"}`,children:"검색"})]}),(F||y)&&e.jsxs("div",{className:"mt-3 border border-slate-100 rounded-xl overflow-hidden",children:[F&&e.jsxs("div",{className:"flex items-center gap-2 p-3 bg-slate-50",children:[e.jsx("div",{className:"w-3.5 h-3.5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"}),e.jsx("span",{className:"text-xs text-slate-500",children:"웹 검색 및 분석 중..."})]}),y&&e.jsxs(e.Fragment,{children:[e.jsx("div",{className:"max-h-64 overflow-y-auto p-3",children:e.jsx(w,{content:y})}),e.jsxs("div",{className:"flex items-center gap-2 px-3 py-2 border-t border-slate-100 bg-slate-50/50",children:[e.jsx("button",{onClick:We,disabled:H,className:`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${H?"bg-green-50 text-green-600 border border-green-200":"btn-primary"}`,children:H?"프로젝트에 저장됨":"프로젝트에 저장"}),e.jsx("button",{onClick:()=>z(y),className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"서식 복사"}),H&&e.jsx("span",{className:"text-[10px] text-slate-400 ml-auto",children:"자료 분석에서 활용 가능"})]})]})]}),ke.length>0&&!y&&e.jsx("div",{className:"mt-2 flex flex-wrap gap-1.5",children:ke.map((t,s)=>e.jsxs("button",{onClick:()=>{we(t.query),O(t.result),ue(t.saved)},className:"px-2 py-1 text-[11px] text-slate-500 bg-slate-50 border border-slate-100 rounded-md hover:bg-slate-100 transition-colors truncate max-w-[200px]",children:[t.saved&&e.jsx("span",{className:"text-green-500 mr-1",children:"✓"}),t.query]},s))})]}),e.jsx("button",{onClick:Fe,className:"w-full py-3 btn-primary rounded-xl text-sm",children:"자료 분석 시작"})]})]})}),m&&S===2&&e.jsxs("div",{className:"animate-fade-in-up space-y-3",children:[B&&e.jsxs("div",{className:"glass-card p-4 flex items-center gap-3",children:[e.jsx("div",{className:"w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"}),e.jsx("span",{className:"text-sm text-slate-500",children:E?`분석 중... (${E.completed}/${E.total}건 완료)`:"분석 준비 중..."}),e.jsx("button",{onClick:Ve,className:"px-3 py-1 bg-red-500 text-white text-xs font-semibold rounded-lg hover:bg-red-600 transition-all",children:"중지"})]}),T.length>0&&e.jsx("div",{className:"space-y-2",children:T.map((t,s)=>e.jsxs("div",{className:"glass-card-elevated overflow-hidden",children:[e.jsxs("button",{onClick:()=>Y(ie===s?null:s),className:"w-full flex items-center justify-between p-4 text-left hover:bg-slate-50/50 transition-colors",children:[e.jsxs("div",{className:"flex items-center gap-2.5",children:[e.jsx("span",{className:"text-base",children:"📄"}),e.jsx("span",{className:"text-sm font-semibold text-slate-700",children:t.filename}),B&&s===T.length-1&&E&&E.completed<E.total&&e.jsx("span",{className:"text-[10px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full font-medium",children:"방금 완료"})]}),e.jsx("svg",{className:`w-4 h-4 text-slate-400 transition-transform ${ie===s?"rotate-180":""}`,viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M4 6l4 4 4-4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})})]}),ie===s&&e.jsxs("div",{className:"px-5 pb-5 border-t border-slate-100",children:[e.jsx("div",{className:"max-h-[50vh] overflow-y-auto pt-4",children:e.jsx(w,{content:t.result})}),e.jsxs("div",{className:"flex gap-2 mt-3 pt-3 border-t border-slate-100",children:[e.jsx("button",{onClick:()=>z(t.result),className:"px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors",children:"서식 복사"}),e.jsx("button",{onClick:()=>U(t.result,A(t.filename,"docx",n)),className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors",children:"Word"})]})]})]},s))}),T.length===0&&R&&!B&&e.jsx("div",{className:"glass-card-elevated p-6",children:e.jsx("div",{className:"max-h-[60vh] overflow-y-auto",children:e.jsx(w,{content:R})})}),!B&&(T.length>0||R)&&e.jsxs("div",{className:"flex gap-2 pt-2",children:[e.jsx("button",{onClick:()=>v(3),className:"px-4 py-2 btn-primary text-sm rounded-lg",children:"자료 Q&A"}),e.jsx("button",{onClick:()=>U(R,A("자료분석","docx",n)),className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"전체 Word 저장"}),e.jsx("button",{onClick:te,className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"전체 MD 저장"})]})]}),m&&S===3&&e.jsxs("div",{className:"flex gap-4 animate-fade-in-up",style:{height:"calc(100vh - 280px)"},children:[e.jsxs("div",{className:"flex-1 glass-card-elevated p-5 overflow-y-auto",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:"분석 결과"}),e.jsx(w,{content:R})]}),e.jsxs("div",{className:"w-96 glass-card-elevated p-4 flex flex-col",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:"자료 기반 Q&A"}),e.jsx(Re,{messages:ce,onSend:He,loading:je,onStop:_e,placeholder:"자료에 대해 질문하세요..."})]})]}),!m&&W==="choice"&&e.jsx("div",{className:"flex items-center justify-center animate-fade-in-up",style:{minHeight:"calc(100vh - 280px)"},children:e.jsxs("div",{className:"flex gap-6",children:[e.jsxs("button",{onClick:()=>{ye("report"),xe(""),I("templates")},className:"group w-72 glass-card-elevated p-8 flex flex-col items-center gap-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden",children:[e.jsx("div",{className:"absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-blue-500 to-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity"}),e.jsx("div",{className:"w-16 h-16 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-300",style:{background:"linear-gradient(135deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))"},children:"📄"}),e.jsxs("div",{children:[e.jsx("div",{className:"text-lg font-bold text-slate-800",children:"보고서 작성"}),e.jsx("div",{className:"text-sm text-slate-500 mt-1",children:"투심보고서, IM, Term Sheet 등"}),e.jsx("div",{className:"text-xs text-blue-500 font-semibold mt-2",children:"10종 템플릿"})]})]}),e.jsxs("button",{onClick:()=>{ye("ppt"),xe(""),I("templates")},className:"group w-72 glass-card-elevated p-8 flex flex-col items-center gap-4 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden",children:[e.jsx("div",{className:"absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-violet-500 to-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"}),e.jsx("div",{className:"w-16 h-16 rounded-2xl flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-300",style:{background:"linear-gradient(135deg, rgba(139,92,246,0.1), rgba(59,130,246,0.1))"},children:"📊"}),e.jsxs("div",{children:[e.jsx("div",{className:"text-lg font-bold text-slate-800",children:"PPT 작성"}),e.jsx("div",{className:"text-sm text-slate-500 mt-1",children:"투자 발표, 논문 발표"}),e.jsx("div",{className:"text-xs text-violet-500 font-semibold mt-2",children:"2종 템플릿"})]})]})]})}),!m&&W==="templates"&&e.jsxs("div",{className:"animate-fade-in-up",children:[e.jsxs("button",{onClick:()=>I("choice"),className:"mb-4 flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all",children:[e.jsx("svg",{className:"w-4 h-4",viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M10 4L6 8l4 4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})}),"돌아가기"]}),e.jsxs("div",{className:"flex gap-5",style:{minHeight:"calc(100vh - 340px)"},children:[e.jsxs("div",{className:"w-[480px] shrink-0 space-y-4 overflow-y-auto pr-1",style:{maxHeight:"calc(100vh - 340px)"},children:[e.jsxs("div",{className:"glass-card p-4",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:de==="report"?"보고서 템플릿":"PPT 템플릿"}),e.jsx("div",{className:`grid gap-2 stagger-children ${de==="report"?"grid-cols-2":"grid-cols-1"}`,children:fe.map(t=>e.jsxs("button",{onClick:()=>{xe(t.id);const s=k[t.id];Z(s?s.map(a=>a.id):[])},className:`text-left p-3 rounded-xl border transition-all duration-200 group ${c===t.id?"border-blue-300 bg-blue-50/70 shadow-sm":"border-slate-100 hover:border-slate-200 hover:bg-slate-50/50"}`,children:[e.jsxs("div",{className:"flex items-center gap-2 mb-0.5",children:[e.jsx("span",{className:"text-base group-hover:scale-110 transition-transform",children:t.icon}),e.jsx("span",{className:`text-sm font-semibold ${c===t.id?"text-blue-700":"text-slate-700"}`,children:t.label})]}),e.jsx("div",{className:"text-xs text-slate-400 pl-7",children:t.desc})]},t.id))})]}),e.jsxs("div",{className:"glass-card overflow-hidden",children:[e.jsxs("button",{onClick:()=>De(!me),className:"w-full flex items-center justify-between p-3.5 text-sm font-semibold text-slate-700 hover:bg-slate-50/50 transition-colors",children:[e.jsxs("span",{className:"flex items-center gap-2",children:[e.jsx("svg",{className:"w-4 h-4 text-slate-400",viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M2 4h12M2 4v8a1 1 0 001 1h10a1 1 0 001-1V4M2 4l2-2h4l2 2",stroke:"currentColor",strokeWidth:"1.2",strokeLinecap:"round"})}),"문서 선택",u.length>0&&e.jsx("span",{className:"text-xs text-blue-500 font-semibold bg-blue-50 px-1.5 py-0.5 rounded-full",children:u.length})]}),e.jsx("svg",{className:`w-4 h-4 text-slate-400 transition-transform ${me?"":"rotate-180"}`,viewBox:"0 0 16 16",fill:"none",children:e.jsx("path",{d:"M4 6l4 4 4-4",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"})})]}),!me&&e.jsx("div",{className:"px-3.5 pb-3 max-h-48 overflow-y-auto border-t border-slate-100",children:e.jsx(Te,{tree:Q,projectName:n,selectable:!0,selectedDocs:u,onSelectionChange:K})})]}),e.jsxs("div",{className:"glass-card p-4",children:[e.jsx("label",{className:"block text-sm font-semibold text-slate-700 mb-2",children:"추가 컨텍스트"}),e.jsx("textarea",{value:re,onChange:t=>$e(t.target.value),placeholder:"보고서에 포함할 추가 정보나 지시사항...",rows:3,className:"w-full px-3 py-2.5 text-sm input-ring resize-none"})]}),e.jsxs("div",{className:"glass-card p-4",children:[e.jsx(Me,{onFilesSelected:Se,loading:ge}),J&&e.jsx("div",{className:"mt-2 text-xs text-slate-500",children:J})]}),e.jsx("button",{onClick:Ge,disabled:!c,className:`w-full py-3.5 rounded-xl text-sm font-semibold transition-all duration-200 ${c?"btn-primary":"bg-slate-100 text-slate-400 cursor-not-allowed"}`,children:"작성 시작"})]}),e.jsx("div",{className:"flex-1 glass-card-elevated p-5 overflow-y-auto",style:{maxHeight:"calc(100vh - 340px)"},children:c&&Pe[c]?e.jsxs("div",{className:"animate-fade-in",children:[e.jsxs("div",{className:"flex items-center gap-2 mb-4 pb-3 border-b border-slate-100",children:[e.jsx("span",{className:"text-lg",children:fe.find(t=>t.id===c)?.icon}),e.jsxs("div",{children:[e.jsx("div",{className:"text-sm font-bold text-slate-700",children:fe.find(t=>t.id===c)?.label}),e.jsx("div",{className:"text-[10px] text-slate-400 uppercase tracking-wider font-medium",children:"Template Preview"})]})]}),k[c]&&e.jsxs("div",{className:"mb-4 p-3 bg-slate-50/80 rounded-xl border border-slate-100",children:[e.jsxs("div",{className:"flex items-center justify-between mb-2.5",children:[e.jsx("span",{className:"text-xs font-bold text-slate-500 uppercase tracking-wider",children:"섹션 선택"}),e.jsx("button",{onClick:()=>{const t=k[c].map(s=>s.id);Z(p.length===t.length?[]:t)},className:"text-[11px] text-blue-500 hover:text-blue-700 font-medium",children:p.length===k[c].length?"전체 해제":"전체 선택"})]}),e.jsx("div",{className:"space-y-1",children:k[c].map(t=>e.jsxs("label",{className:`flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-all ${p.includes(t.id)?"bg-blue-50/80 border border-blue-200":"hover:bg-white border border-transparent"}`,children:[e.jsx("input",{type:"checkbox",checked:p.includes(t.id),onChange:()=>{Z(s=>s.includes(t.id)?s.filter(a=>a!==t.id):[...s,t.id])},className:"w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 focus:ring-1"}),e.jsx("span",{className:`text-sm ${p.includes(t.id)?"font-semibold text-blue-700":"text-slate-600"}`,children:t.label})]},t.id))}),p.length>0&&p.length<k[c].length&&e.jsxs("div",{className:"mt-2 text-[11px] text-amber-600 bg-amber-50 px-2.5 py-1.5 rounded-md",children:[k[c].length,"개 중 ",p.length,"개 섹션 선택됨"]})]}),e.jsx(w,{content:Pe[c]})]}):e.jsxs("div",{className:"flex flex-col items-center justify-center h-full text-slate-400",children:[e.jsxs("svg",{className:"w-10 h-10 mb-3 opacity-30",viewBox:"0 0 24 24",fill:"none",children:[e.jsx("path",{d:"M9 12h6M9 16h6M13 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V11",stroke:"currentColor",strokeWidth:"1.5",strokeLinecap:"round"}),e.jsx("path",{d:"M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z",stroke:"currentColor",strokeWidth:"1.5"})]}),e.jsx("span",{className:"text-sm",children:"템플릿을 선택하면 미리보기가 표시됩니다"})]})})]})]}),!m&&W==="generate"&&e.jsxs("div",{className:"glass-card-elevated p-6 animate-fade-in-up",children:[le&&e.jsx(Je,{streamingText:q,startTime:Ie,onStop:ze}),e.jsx("div",{className:"max-h-[60vh] overflow-y-auto",children:e.jsx(w,{content:q||i})}),!le&&i&&e.jsxs("div",{className:"flex gap-2 mt-4 pt-4 border-t border-slate-100",children:[e.jsx("button",{onClick:()=>I("refine"),className:"px-4 py-2 btn-primary text-sm rounded-lg",children:"수정/보완"}),e.jsx("button",{onClick:()=>z(i),className:"px-4 py-2 text-sm text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors",children:"서식 복사"}),e.jsx("button",{onClick:()=>U(i,A(h||"보고서","docx",n)),className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"Word"}),e.jsx("button",{onClick:te,className:"px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"MD"})]})]}),!m&&W==="refine"&&e.jsxs("div",{className:"flex gap-4 animate-fade-in-up",style:{height:"calc(100vh - 280px)"},children:[e.jsxs("div",{className:"flex-1 glass-card-elevated flex flex-col overflow-hidden",children:[e.jsxs("div",{className:"flex items-center justify-between px-5 pt-4 pb-2",children:[e.jsxs("div",{className:"flex items-center gap-2",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider",children:"현재 보고서"}),$&&$!==i&&e.jsx("button",{onClick:()=>Ne(!L),className:`px-2 py-0.5 text-[10px] font-medium rounded-full transition-colors ${L?"bg-amber-100 text-amber-700 border border-amber-200":"bg-slate-100 text-slate-500 border border-slate-200"}`,children:L?"변경 표시 ON":"변경 표시 OFF"})]}),e.jsxs("div",{className:"flex gap-1.5",children:[e.jsx("button",{onClick:()=>z(i),className:"px-2.5 py-1 text-[11px] font-medium text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors",children:"서식복사"}),e.jsx("button",{onClick:()=>U(i,A(h||"보고서","docx",n)),className:"px-2.5 py-1 text-[11px] font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors",children:"Word"}),e.jsx("button",{onClick:te,className:"px-2.5 py-1 text-[11px] font-medium text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors",children:"MD"})]})]}),e.jsx("div",{className:"flex-1 px-5 pb-5 overflow-y-auto",children:e.jsx(w,{content:Qe})})]}),e.jsxs("div",{className:"w-96 glass-card-elevated p-4 flex flex-col",children:[e.jsx("div",{className:"text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3",children:"수정 요청"}),e.jsx(Re,{messages:ce,onSend:Ue,loading:je,onStop:_e,placeholder:"수정할 내용을 입력하세요..."})]})]}),!m&&W==="result"&&e.jsxs("div",{className:"glass-card-elevated p-6 animate-fade-in-up",children:[e.jsxs("div",{className:"flex items-center justify-between mb-4 pb-4 border-b border-slate-100",children:[e.jsxs("div",{className:"flex items-center gap-2",children:[e.jsx("div",{className:"w-8 h-8 rounded-lg flex items-center justify-center gradient-accent text-white text-sm",children:"📄"}),e.jsx("span",{className:"text-sm font-bold text-slate-700",children:"최종 결과"})]}),e.jsxs("div",{className:"flex gap-2",children:[e.jsx("button",{onClick:()=>I("refine"),className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"수정/보완"}),e.jsx("button",{onClick:()=>U(i,A(h||"보고서","docx",n)),className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"Word"}),e.jsx("button",{onClick:te,className:"px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors",children:"MD"}),e.jsx("button",{onClick:()=>z(i),className:"px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors",children:"복사"})]})]}),e.jsx("div",{className:"max-h-[60vh] overflow-y-auto",children:e.jsx(w,{content:i})})]})]})}export{ct as default};
