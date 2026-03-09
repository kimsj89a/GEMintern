import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import { subscribeTask, unsubscribeTask } from '../api/ws';
import FolderTree from '../components/FolderTree';
import ChatWidget from '../components/ChatWidget';
import type { ChatMessage } from '../components/ChatWidget';
import { getLocalFolderTree, getProjectDocuments } from '../utils/projectDB';

export default function QaSessionPage() {
  const { currentProject } = useAppStore();
  const [tree, setTree] = useState<Record<string, string[]>>({});
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [docCount, setDocCount] = useState(0);
  const cancelledRef = useRef(false);
  const activeTaskRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!currentProject) return;
    getLocalFolderTree(currentProject).then(setTree).catch(() => setTree({}));
    getProjectDocuments(currentProject).then(docs => {
      setDocCount(docs.filter(d => d.filename !== '__folder_placeholder__').length);
    }).catch(() => setDocCount(0));
  }, [currentProject]);

  const handleSend = async (question: string) => {
    if (!currentProject) return;
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setLoading(true);
    setStreamingText('');
    cancelledRef.current = false;

    try {
      const { task_id } = await api.startQa({
        project_name: currentProject,
        question,
        selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
      });
      activeTaskRef.current = task_id;

      subscribeTask(task_id, (msg) => {
        if (cancelledRef.current) { unsubscribeTask(task_id); return; }
        if (msg.type === 'chunk' && msg.data) {
          setStreamingText((prev) => prev + msg.data);
        } else if (msg.type === 'complete') {
          const finalText = msg.result || '';
          setMessages((prev) => [...prev, { role: 'assistant', content: finalText }]);
          setStreamingText('');
          setLoading(false);
          unsubscribeTask(task_id);
        } else if (msg.type === 'error') {
          setMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${msg.error}` }]);
          setStreamingText('');
          setLoading(false);
          unsubscribeTask(task_id);
        }
      });

      // Fallback: poll if WebSocket doesn't deliver
      pollRef.current = setInterval(async () => {
        if (cancelledRef.current) { if (pollRef.current) clearInterval(pollRef.current); return; }
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          if (pollRef.current) clearInterval(pollRef.current);
          if (loading) {
            setMessages((prev) => [...prev, { role: 'assistant', content: status.result || '' }]);
            setStreamingText('');
            setLoading(false);
          }
        } else if (status.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current);
          if (loading) {
            setMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${status.error}` }]);
            setStreamingText('');
            setLoading(false);
          }
        }
      }, 3000);

      // Cleanup poll after 5 minutes
      setTimeout(() => { if (pollRef.current) clearInterval(pollRef.current); }, 300000);
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${err.message}` }]);
      setLoading(false);
    }
  };

  const handleStop = () => {
    cancelledRef.current = true;
    if (activeTaskRef.current) unsubscribeTask(activeTaskRef.current);
    if (pollRef.current) clearInterval(pollRef.current);
    if (streamingText) {
      setMessages((prev) => [...prev, { role: 'assistant', content: streamingText + '\n\n*(중지됨)*' }]);
    }
    setStreamingText('');
    setLoading(false);
  };

  const handleClearChat = () => {
    setMessages([]);
    setStreamingText('');
  };

  if (!currentProject) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <h1 className="text-xl font-bold text-[#37352F] mb-2">💬 자료기반 Q&A</h1>
        <div className="text-sm text-[#9B9A97] py-8 text-center">프로젝트를 먼저 선택하세요.</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-[#37352F] mb-1">💬 자료기반 Q&A</h1>
          <p className="text-sm text-[#787774]">
            📂 {currentProject} &middot; 문서 {docCount}건
            {selectedDocs.length > 0 && ` · 선택 ${selectedDocs.length}건`}
          </p>
        </div>
        <button
          onClick={handleClearChat}
          className="px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3]"
        >
          대화 초기화
        </button>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Left: Document selector */}
        <div className="w-64 shrink-0 bg-white border border-[#E9E9E7] rounded-xl p-3 overflow-y-auto">
          <div className="text-xs font-semibold text-[#9B9A97] uppercase mb-2">문서 선택</div>
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

        {/* Right: Chat */}
        <div className="flex-1 bg-white border border-[#E9E9E7] rounded-xl p-4 flex flex-col min-h-0">
          <ChatWidget
            messages={messages}
            onSend={handleSend}
            loading={loading}
            onStop={handleStop}
            streamingText={streamingText}
            placeholder="선택한 문서에 대해 질문하세요..."
          />
        </div>
      </div>
    </div>
  );
}
