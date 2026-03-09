import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import FolderTree from '../components/FolderTree';
import MarkdownViewer from '../components/MarkdownViewer';
import { copyRichText, downloadAsWord } from '../utils/clipboard';
import { getLocalFolderTree } from '../utils/projectDB';
import { useAutoSync } from '../utils/autoSync';

interface QaItem {
  question: string;
  answer: string;
  status: 'pending' | 'generating' | 'done' | 'error';
}

export default function LpQaPage() {
  const { currentProject } = useAppStore();
  useAutoSync(currentProject);
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [inputMode, setInputMode] = useState<'direct' | 'file'>('direct');
  const [questionsText, setQuestionsText] = useState('');
  const [questionsList, setQuestionsList] = useState<string[]>([]);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [qaItems, setQaItems] = useState<QaItem[]>([]);
  const [generating, setGenerating] = useState(false);
  const cancelledRef = useRef(false);
  const queueRef = useRef<QaItem[]>([]);
  const processingRef = useRef(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  useEffect(() => {
    if (!currentProject) return;
    getLocalFolderTree(currentProject).then(setTree).catch(() => setTree({}));
  }, [currentProject]);

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
      // Excel/CSV
      const result = await api.extractExcelCells([file]);
      if (result.cells.length > 0) {
        setQuestionsList(result.cells);
      } else {
        setQuestionsList(['파일에서 질문을 추출할 수 없습니다.']);
      }
    } catch {
      setQuestionsList(['파일 업로드 실패']);
    }
    setUploading(false);
  };

  const removeQuestion = (idx: number) => {
    setQuestionsList(prev => prev.filter((_, i) => i !== idx));
  };

  const startEdit = (idx: number) => {
    setEditingIdx(idx);
    setEditText(questionsList[idx]);
  };

  const saveEdit = () => {
    if (editingIdx === null) return;
    setQuestionsList(prev => prev.map((q, i) => i === editingIdx ? editText.trim() : q));
    setEditingIdx(null);
    setEditText('');
  };

  const cancelEdit = () => {
    setEditingIdx(null);
    setEditText('');
  };

  const clearQuestionsList = () => {
    setQuestionsList([]);
  };

  const syncDisplay = () => {
    setQaItems([...queueRef.current]);
  };

  const pollTask = (taskId: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const check = async () => {
        if (cancelledRef.current) { reject(new Error('cancelled')); return; }
        try {
          const status = await api.getTaskStatus(taskId);
          if (status.status === 'complete') resolve(status.result || '');
          else if (status.status === 'error') reject(new Error(status.error || '생성 실패'));
          else setTimeout(check, 1000);
        } catch (err) {
          reject(err);
        }
      };
      check();
    });
  };

  const processQueue = async () => {
    if (processingRef.current) return;
    processingRef.current = true;
    setGenerating(true);
    cancelledRef.current = false;

    while (true) {
      const idx = queueRef.current.findIndex((it) => it.status === 'pending');
      if (idx === -1 || cancelledRef.current) break;

      queueRef.current[idx].status = 'generating';
      syncDisplay();

      try {
        const { task_id } = await api.startQa({
          project_name: currentProject!,
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
    if (!currentProject) return;

    // 직접 입력 모드: questionsText에서, 파일 모드: questionsList에서
    let questions: string[];
    if (inputMode === 'file' && questionsList.length > 0) {
      questions = questionsList.filter(q => q.trim());
      setQuestionsList([]);
    } else {
      questions = questionsText.split('\n').map((q) => q.trim()).filter(Boolean);
      setQuestionsText('');
    }
    if (questions.length === 0) return;

    const newItems: QaItem[] = questions.map((q) => ({ question: q, answer: '', status: 'pending' as const }));
    queueRef.current = [...queueRef.current, ...newItems];
    syncDisplay();

    if (!processingRef.current) {
      processQueue();
    }
  };

  const handleStop = () => {
    cancelledRef.current = true;
  };

  const handleClearAll = () => {
    if (generating) return;
    queueRef.current = [];
    setQaItems([]);
  };

  const copyToClipboard = (text: string, idx: number) => {
    copyRichText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  const exportSingle = (item: QaItem, idx: number) => {
    const text = `## Q${idx + 1}. ${item.question}\n\n${item.answer}`;
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `qa_${idx + 1}.md`; a.click();
    URL.revokeObjectURL(url);
  };

  const exportAll = () => {
    const done = qaItems.filter((it) => it.status === 'done' || it.status === 'error');
    if (done.length === 0) return;
    const text = qaItems.map((it, i) =>
      `## Q${i + 1}. ${it.question}\n\n${it.answer}`
    ).join('\n\n---\n\n');
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'lp_qa_all.md'; a.click();
    URL.revokeObjectURL(url);
  };

  const exportAllWord = () => {
    const done = qaItems.filter((it) => it.status === 'done' || it.status === 'error');
    if (done.length === 0) return;
    const text = '# LP Q&A 답변 모음\n\n' + qaItems.map((it, i) =>
      `## Q${i + 1}. ${it.question}\n\n${it.answer}`
    ).join('\n\n---\n\n');
    downloadAsWord(text, 'LP_QA_All.docx');
  };

  const doneCount = qaItems.filter((it) => it.status === 'done' || it.status === 'error').length;
  const totalCount = qaItems.length;
  const progressPct = totalCount > 0 ? (doneCount / totalCount) * 100 : 0;

  const hasQuestions = inputMode === 'file' ? questionsList.length > 0 : questionsText.trim().length > 0;

  if (!currentProject) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <h1 className="text-xl font-bold text-[#37352F] mb-2">🙋 LP Q&A 대응</h1>
        <div className="text-sm text-[#9B9A97] py-8 text-center">프로젝트를 먼저 선택하세요.</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">🙋 LP Q&A 대응</h1>
      <p className="text-sm text-[#787774] mb-6">질문 목록을 입력하면 문서 기반으로 일괄 답변을 생성합니다. 생성 중에도 추가 질문을 넣을 수 있습니다.</p>

      <div className="flex gap-6">
        {/* Left: Document selector */}
        <div className="w-64 shrink-0">
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-3 max-h-80 overflow-y-auto">
            <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">참조 문서</div>
            {Object.keys(tree).length > 0 ? (
              <FolderTree
                tree={tree}
                projectName={currentProject}
                selectable
                selectedDocs={selectedDocs}
                onSelectionChange={setSelectedDocs}
              />
            ) : (
              <div className="text-xs text-[#9B9A97] py-4 text-center">문서가 없습니다.</div>
            )}
          </div>
        </div>

        {/* Right: Input + Results */}
        <div className="flex-1">
          {/* Input mode tabs */}
          <div className="flex gap-2 mb-3">
            <button
              onClick={() => setInputMode('direct')}
              className={`px-3 py-1.5 text-sm rounded-lg ${inputMode === 'direct' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}
            >
              직접 입력
            </button>
            <button
              onClick={() => setInputMode('file')}
              className={`px-3 py-1.5 text-sm rounded-lg ${inputMode === 'file' ? 'bg-[#2383E2] text-white' : 'border border-[#E9E9E7] hover:bg-[#F7F6F3]'}`}
            >
              파일 업로드
            </button>
          </div>

          {/* Input area */}
          <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
            {inputMode === 'direct' ? (
              <textarea
                value={questionsText}
                onChange={(e) => setQuestionsText(e.target.value)}
                placeholder="질문을 줄 단위로 입력하세요.&#10;예:&#10;투자 구조는 어떻게 되나요?&#10;리스크 요인은 무엇인가요?"
                rows={4}
                className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
              />
            ) : (
              <div>
                <label className={`inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3] ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
                  {uploading ? '⏳ 파싱 중...' : '📂 텍스트/Excel 파일 선택'}
                  <input type="file" accept=".txt,.csv,.xlsx" onChange={handleFileUpload} className="hidden" disabled={uploading} />
                </label>
              </div>
            )}
          </div>

          {/* Question preview list (file upload mode) */}
          {inputMode === 'file' && questionsList.length > 0 && (
            <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-medium text-[#37352F]">
                  질문 목록 ({questionsList.length}개)
                </div>
                <button onClick={clearQuestionsList} className="text-xs text-[#EB5757] hover:underline">
                  전체 삭제
                </button>
              </div>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {questionsList.map((q, i) => (
                  <div key={i} className="flex items-start gap-2 group">
                    <span className="text-xs text-[#9B9A97] mt-1.5 shrink-0 w-6 text-right">{i + 1}.</span>
                    {editingIdx === i ? (
                      <div className="flex-1">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={3}
                          className="w-full px-2 py-1.5 text-sm border border-[#2383E2] rounded-lg focus:outline-none resize-none"
                          autoFocus
                        />
                        <div className="flex gap-1 mt-1">
                          <button onClick={saveEdit}
                            className="px-2 py-0.5 text-xs bg-[#2383E2] text-white rounded hover:bg-[#1b6ec2]">
                            저장
                          </button>
                          <button onClick={cancelEdit}
                            className="px-2 py-0.5 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">
                            취소
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex-1 text-sm text-[#37352F] whitespace-pre-wrap leading-relaxed py-1">
                          {q}
                        </div>
                        <div className="flex gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => startEdit(i)}
                            className="px-1.5 py-0.5 text-xs text-[#9B9A97] hover:text-[#2383E2] hover:bg-blue-50 rounded"
                            title="수정">
                            ✏️
                          </button>
                          <button onClick={() => removeQuestion(i)}
                            className="px-1.5 py-0.5 text-xs text-[#9B9A97] hover:text-[#EB5757] hover:bg-red-50 rounded"
                            title="삭제">
                            🗑
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Generate / Stop buttons */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={handleGenerate}
              disabled={!hasQuestions}
              className="flex-1 py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors"
            >
              {generating ? '🤖 추가 질문 투입' : '🤖 답변 생성'}
            </button>
            {generating && (
              <button onClick={handleStop}
                className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
                중지
              </button>
            )}
          </div>

          {/* Progress bar */}
          {generating && totalCount > 0 && (
            <div className="mb-4">
              <div className="text-xs text-[#787774] mb-1">진행 중... {doneCount}/{totalCount}</div>
              <div className="w-full bg-[#E9E9E7] rounded-full h-1.5">
                <div className="bg-[#2383E2] h-1.5 rounded-full transition-all" style={{ width: `${progressPct}%` }} />
              </div>
            </div>
          )}

          {/* Results */}
          {qaItems.length > 0 && (
            <div className="space-y-3">
              {/* Export / Clear buttons */}
              {qaItems.some((it) => it.status === 'done') && (
                <div className="flex justify-end gap-2">
                  {!generating && (
                    <button
                      onClick={handleClearAll}
                      className="px-3 py-1.5 text-xs border border-[#EB5757] text-[#EB5757] rounded-lg hover:bg-red-50"
                    >
                      전체 삭제
                    </button>
                  )}
                  <button
                    onClick={exportAllWord}
                    className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] text-[#787774]"
                  >
                    📄 전체 Word 저장
                  </button>
                  <button
                    onClick={exportAll}
                    className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] text-[#787774]"
                  >
                    전체 내보내기 (.md)
                  </button>
                </div>
              )}
              {qaItems.map((item, i) => (
                <div key={i} className="bg-white border border-[#E9E9E7] rounded-xl p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-[#2383E2]">
                      {item.status === 'generating' && (
                        <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                      )}
                      Q{i + 1}. {item.question}
                    </div>
                    {item.status === 'done' && (
                      <div className="flex gap-1 shrink-0 ml-2">
                        <button
                          onClick={() => copyToClipboard(item.answer, i)}
                          className="px-2 py-0.5 text-xs text-[#9B9A97] hover:text-[#37352F] hover:bg-[#F7F6F3] rounded transition-colors"
                        >
                          {copiedIdx === i ? '복사됨' : '복사'}
                        </button>
                        <button
                          onClick={() => exportSingle(item, i)}
                          className="px-2 py-0.5 text-xs text-[#9B9A97] hover:text-[#37352F] hover:bg-[#F7F6F3] rounded transition-colors"
                        >
                          내보내기
                        </button>
                      </div>
                    )}
                  </div>
                  {item.status === 'generating' && (
                    <div className="text-sm text-[#9B9A97]">생성 중...</div>
                  )}
                  {item.status === 'pending' && (
                    <div className="text-sm text-[#9B9A97]">대기 중</div>
                  )}
                  {(item.status === 'done' || item.status === 'error') && (
                    <MarkdownViewer content={item.answer} />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
