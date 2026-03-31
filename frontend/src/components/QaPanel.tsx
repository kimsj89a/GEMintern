import { useRef, useState } from 'react';
import { api } from '../api/client';
import MarkdownViewer from './MarkdownViewer';
import { copyRichText, downloadAsWord, downloadAsMd, generateFilename } from '../utils/clipboard';

interface QaItem {
  question: string;
  answer: string;
  status: 'pending' | 'generating' | 'done' | 'error';
}

export default function QaPanel({ projectName, selectedDocs }: {
  projectName: string;
  selectedDocs: string[];
}) {
  const [inputMode, setInputMode] = useState<'direct' | 'file'>('direct');
  const [questionsText, setQuestionsText] = useState('');
  const [questionsList, setQuestionsList] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [qaItems, setQaItems] = useState<QaItem[]>([]);
  const [generating, setGenerating] = useState(false);
  const cancelledRef = useRef(false);
  const queueRef = useRef<QaItem[]>([]);
  const processingRef = useRef(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const syncDisplay = () => setQaItems([...queueRef.current]);

  const pollTask = (taskId: string): Promise<string> =>
    new Promise((resolve, reject) => {
      const check = async () => {
        if (cancelledRef.current) { reject(new Error('cancelled')); return; }
        try {
          const s = await api.getTaskStatus(taskId);
          if (s.status === 'complete') resolve(s.result || '');
          else if (s.status === 'error') reject(new Error(s.error || '생성 실패'));
          else setTimeout(check, 1500);
        } catch (err) { reject(err); }
      };
      check();
    });

  const processQueue = async () => {
    if (processingRef.current) return;
    processingRef.current = true;
    setGenerating(true);
    cancelledRef.current = false;

    while (true) {
      const idx = queueRef.current.findIndex(it => it.status === 'pending');
      if (idx === -1 || cancelledRef.current) break;
      queueRef.current[idx].status = 'generating';
      syncDisplay();
      try {
        const { task_id } = await api.startQa({
          project_name: projectName,
          question: queueRef.current[idx].question,
          selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
        });
        const result = await pollTask(task_id);
        if (cancelledRef.current) break;
        queueRef.current[idx].answer = result;
        queueRef.current[idx].status = 'done';
      } catch (err: any) {
        if (cancelledRef.current) break;
        queueRef.current[idx].answer = `오류: ${err.message}`;
        queueRef.current[idx].status = 'error';
      }
      syncDisplay();
    }

    if (cancelledRef.current) {
      for (const item of queueRef.current) {
        if (item.status === 'generating') item.status = 'pending';
      }
      syncDisplay();
    }
    processingRef.current = false;
    setGenerating(false);
  };

  const handleGenerate = () => {
    if (!projectName) return;
    let questions: string[];
    if (inputMode === 'file' && questionsList.length > 0) {
      questions = questionsList.filter(q => q.trim());
      setQuestionsList([]);
    } else {
      questions = questionsText.split('\n').map(q => q.trim()).filter(Boolean);
      setQuestionsText('');
    }
    if (questions.length === 0) return;
    const newItems: QaItem[] = questions.map(q => ({ question: q, answer: '', status: 'pending' as const }));
    queueRef.current = [...queueRef.current, ...newItems];
    syncDisplay();
    if (!processingRef.current) processQueue();
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    setUploading(true);
    try {
      if (ext === 'txt') {
        const reader = new FileReader();
        reader.onload = () => {
          const lines = (reader.result as string).split('\n').map(l => l.trim()).filter(Boolean);
          setQuestionsList(lines);
          setUploading(false);
        };
        reader.readAsText(file);
        return;
      }
      const result = await api.extractExcelCells([file]);
      setQuestionsList(result.cells.length > 0 ? result.cells : ['파일에서 질문을 추출할 수 없습니다.']);
    } catch {
      setQuestionsList(['파일 업로드 실패']);
    }
    setUploading(false);
  };

  const exportAll = (format: 'word' | 'md' = 'word') => {
    const done = qaItems.filter(it => it.status === 'done');
    if (!done.length) return;
    const md = done.map((it, i) => `## Q${i + 1}. ${it.question}\n\n${it.answer}`).join('\n\n---\n\n');
    const fname = generateFilename('질의회신', format === 'word' ? 'docx' : 'md', projectName);
    if (format === 'word') downloadAsWord(md, fname);
    else downloadAsMd(md, fname);
  };

  const doneCount = qaItems.filter(it => it.status === 'done').length;
  const totalCount = qaItems.length;
  const progress = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* 결과 영역 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {qaItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <span className="text-4xl mb-3 opacity-40">📋</span>
            <span className="text-sm">아래에서 질문을 입력하거나 파일을 업로드하세요</span>
            <span className="text-xs mt-1">줄 단위로 질문이 분리되어 배치 처리됩니다</span>
          </div>
        ) : (
          <>
            {/* 진행 바 */}
            {generating && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-blue-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
                <span className="text-xs text-blue-600 font-medium shrink-0">{doneCount}/{totalCount}</span>
                <button onClick={() => { cancelledRef.current = true; }}
                  className="text-xs text-red-500 hover:text-red-700 shrink-0">중지</button>
              </div>
            )}

            {/* 내보내기 */}
            {doneCount > 0 && !generating && (
              <div className="flex gap-2 justify-end">
                <button onClick={() => exportAll('md')}
                  className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                  MD
                </button>
                <button onClick={() => exportAll('word')}
                  className="px-3 py-1 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50">
                  Word
                </button>
                <button onClick={() => { queueRef.current = []; setQaItems([]); }}
                  className="px-3 py-1 text-xs text-slate-400 border border-slate-200 rounded-lg hover:bg-slate-50">
                  초기화
                </button>
              </div>
            )}

            {/* Q&A 카드 */}
            {qaItems.map((item, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    item.status === 'done' ? 'bg-green-500' :
                    item.status === 'generating' ? 'bg-blue-500 animate-pulse' :
                    item.status === 'error' ? 'bg-red-500' : 'bg-slate-300'
                  }`} />
                  <span className="text-sm font-medium text-slate-700 truncate flex-1">Q{i + 1}. {item.question}</span>
                  {item.status === 'done' && (
                    <button onClick={() => { copyRichText(item.answer); setCopiedIdx(i); setTimeout(() => setCopiedIdx(null), 1500); }}
                      className="text-[10px] text-slate-400 hover:text-blue-600">
                      {copiedIdx === i ? '✓' : '복사'}
                    </button>
                  )}
                </div>
                {item.answer && (
                  <div className="px-4 py-3">
                    <MarkdownViewer content={item.answer} />
                  </div>
                )}
                {item.status === 'generating' && (
                  <div className="px-4 py-3 flex items-center gap-2 text-slate-400">
                    <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs">답변 생성 중...</span>
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </div>

      {/* 하단 입력 */}
      <div className="border-t border-slate-200 p-3 space-y-2 shrink-0 bg-white">
        {/* 모드 토글 */}
        <div className="flex items-center gap-2">
          <button onClick={() => setInputMode('direct')}
            className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${inputMode === 'direct' ? 'bg-blue-50 text-blue-700 font-medium' : 'text-slate-500 hover:bg-slate-50'}`}>
            직접 입력
          </button>
          <button onClick={() => setInputMode('file')}
            className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${inputMode === 'file' ? 'bg-blue-50 text-blue-700 font-medium' : 'text-slate-500 hover:bg-slate-50'}`}>
            파일 업로드
          </button>
          {selectedDocs.length > 0 && (
            <span className="text-[10px] text-slate-400 ml-auto">{selectedDocs.length}개 문서 선택</span>
          )}
        </div>

        {inputMode === 'direct' ? (
          <div className="flex gap-2">
            <textarea
              value={questionsText}
              onChange={e => setQuestionsText(e.target.value)}
              placeholder="질문을 입력하세요 (줄 단위로 분리)..."
              rows={2}
              className="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-blue-400 resize-none"
            />
            <button onClick={handleGenerate} disabled={generating || !questionsText.trim()}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-30 shrink-0">
              생성
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <label className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border-2 border-dashed border-slate-200 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
              <span className="text-xs text-slate-500">{uploading ? '업로드 중...' : questionsList.length > 0 ? `${questionsList.length}개 질문 로드됨` : 'Excel/TXT 파일 선택'}</span>
              <input type="file" accept=".xlsx,.xls,.csv,.txt" onChange={handleFileUpload} className="hidden" />
            </label>
            <button onClick={handleGenerate} disabled={generating || questionsList.length === 0}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-30 shrink-0">
              생성
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
