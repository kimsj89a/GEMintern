import { lazy } from 'react';

export const PAGE_REGISTRY: Record<
  string,
  { label: string; component: React.LazyExoticComponent<any> }
> = {
  home: { label: '🏠 홈', component: lazy(() => import('./HomePage')) },
  settings: { label: '⚙️ 설정', component: lazy(() => import('./SettingsPage')) },
  project: { label: '📂 프로젝트', component: lazy(() => import('./ProjectPage')) },
  phase1: { label: '📥 사전 정보 수집', component: lazy(() => import('./WorkflowPage')) },
  phase2: { label: '📝 문서 작성', component: lazy(() => import('./WorkflowPage')) },
  freedoc: { label: '📝 자유양식 문서', component: lazy(() => import('./FreeDocPage')) },
  lp_qa: { label: '🙋‍♂️ LP Q&A', component: lazy(() => import('./LpQaPage')) },
  qa_session: { label: '💬 자료기반 Q&A', component: lazy(() => import('./QaSessionPage')) },
  audio: { label: '🎤 오디오 전사', component: lazy(() => import('./AudioPage')) },
  crawler: { label: '🌐 웹 크롤러', component: lazy(() => import('./CrawlerPage')) },
  ocr: { label: '👁️ 문서 OCR', component: lazy(() => import('./OcrPage')) },
  markdown: { label: '📝 MD to Word', component: lazy(() => import('./MarkdownPage')) },
  doctemplate: { label: '📋 문서양식', component: lazy(() => import('./DocTemplatePage')) },
  text_organizer: { label: '✏️ 문장 정리기', component: lazy(() => import('./TextOrganizerPage')) },
  doc_updater: { label: '🔄 문서 업데이트', component: lazy(() => import('./DocUpdaterPage')) },
  nps: { label: '🏢 국민연금 사업장', component: lazy(() => import('./NpsPage')) },
  quickmail: { label: '✉️ QuickMail', component: lazy(() => import('./QuickMailPage')) },
  dartwings: { label: '📊 DartWings', component: lazy(() => import('./DartwingsPage')) },
  draftdoc: { label: '📄 기안문 작성', component: lazy(() => import('./DraftDocPage')) },
  ppt_tools: { label: '📊 발표자료 (PPT)', component: lazy(() => import('./PptToolsPage')) },
  pdf_unlock: { label: 'PDF 잠금 해제', component: lazy(() => import('./PdfUnlockPage')) },
  history: { label: '생성 이력', component: lazy(() => import('./HistoryPage')) },
  admin: { label: '🛡️ 관리자', component: lazy(() => import('./AdminPage')) },
};
