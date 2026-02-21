import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import FolderTree from '../components/FolderTree';
import MarkdownViewer from '../components/MarkdownViewer';

interface QaItem {
  question: string;
  answer: string;
  status: 'pending' | 'generating' | 'done' | 'error';
}

export default function LpQaPage() {
  const { currentProject } = useAppStore();
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [inputMode, setInputMode] = useState<'direct' | 'file'>('direct');
  const [questionsText, setQuestionsText] = useState('');
  const [qaItems, setQaItems] = useState<QaItem[]>([]);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const cancelledRef = useRef(false);

  useEffect(() => {
    if (!currentProject) return;
    api.getProjectDocs(currentProject).then((data) => {
      setTree(data.folder_tree || {});
    }).catch(() => {});
  }, [currentProject]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setQuestionsText(reader.result as string);
    };
    reader.readAsText(file);
  };

  const handleGenerate = async () => {
    if (!currentProject || !questionsText.trim()) return;
    const questions = questionsText.split('\n').map((q) => q.trim()).filter(Boolean);
    if (questions.length === 0) return;

    const items: QaItem[] = questions.map((q) => ({ question: q, answer: '', status: 'pending' }));
    setQaItems(items);
    setGenerating(true);
    setProgress(0);
    cancelledRef.current = false;

    for (let i = 0; i < items.length; i++) {
      if (cancelledRef.current) break;
      items[i].status = 'generating';
      setQaItems([...items]);

      try {
        const { task_id } = await api.startQa({
          project_name: currentProject,
          question: items[i].question,
          selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
        });

        let result = await pollTask(task_id);
        if (cancelledRef.current) break;
        items[i].answer = result;
        items[i].status = 'done';
      } catch (err: any) {
        if (cancelledRef.current) break;
        items[i].answer = `오류: ${err.message}`;
        items[i].status = 'error';
      }

      setProgress(((i + 1) / items.length) * 100);
      setQaItems([...items]);
    }

    if (cancelledRef.current) {
      // Mark remaining as pending
      for (const item of items) {
        if (item.status === 'generating') item.status = 'pending';
      }
      setQaItems([...items]);
    }
    setGenerating(false);
  };

  const handleStop = () => {
    cancelledRef.current = true;
    setGenerating(false);
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

  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
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
      <p className="text-sm text-[#787774] mb-6">질문 목록을 입력하면 문서 기반으로 일괄 답변을 생성합니다.</p>

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
                rows={6}
                className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none"
              />
            ) : (
              <div>
                <label className="inline-block px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3]">
                  📂 텍스트/Excel 파일 선택
                  <input type="file" accept=".txt,.csv,.xlsx" onChange={handleFileUpload} className="hidden" />
                </label>
                {questionsText && (
                  <div className="mt-2 text-xs text-[#9B9A97]">
                    {questionsText.split('\n').filter(Boolean).length}개 질문 로드됨
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Generate / Stop button */}
          {generating ? (
            <div className="flex gap-2 mb-4">
              <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
                생성 중... ({Math.round(progress)}%)
              </div>
              <button onClick={handleStop}
                className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
                중지
              </button>
            </div>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={!questionsText.trim()}
              className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4"
            >
              🤖 답변 생성
            </button>
          )}

          {/* Progress bar */}
          {generating && (
            <div className="w-full bg-[#E9E9E7] rounded-full h-1.5 mb-4">
              <div className="bg-[#2383E2] h-1.5 rounded-full transition-all" style={{ width: `${progress}%` }} />
            </div>
          )}

          {/* Results */}
          {qaItems.length > 0 && (
            <div className="space-y-3">
              {/* Export all button */}
              {qaItems.some((it) => it.status === 'done') && (
                <div className="flex justify-end">
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
                    <div className="text-sm font-medium text-[#2383E2]">Q{i + 1}. {item.question}</div>
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
