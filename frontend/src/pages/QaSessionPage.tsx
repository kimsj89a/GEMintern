import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { api } from '../api/client';
import { subscribeTask, unsubscribeTask } from '../api/ws';
import FolderTree from '../components/FolderTree';
import ChatWidget, { ChatInputBar } from '../components/ChatWidget';
import type { ChatMessage } from '../components/ChatWidget';

interface QaSession {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

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

  // Session state
  const [sessions, setSessions] = useState<QaSession[]>([]);
  const [activeSession, setActiveSession] = useState<number | null>(null);
  const [sessionsOpen, setSessionsOpen] = useState(true);

  // Load folder tree from server & select all docs by default
  useEffect(() => {
    if (!currentProject) return;
    api.getProjectDocs(currentProject).then(data => {
      const folderTree = data.folder_tree || {};
      setTree(folderTree);
      setDocCount(data.count || 0);
      // 기본: 모든 문서 선택
      const allDocs = Object.values(folderTree).flat() as string[];
      setSelectedDocs(allDocs);
    }).catch(() => { setTree({}); setDocCount(0); setSelectedDocs([]); });
  }, [currentProject]);

  // Load sessions when project changes
  useEffect(() => {
    if (!currentProject) { setSessions([]); setActiveSession(null); return; }
    loadSessions();
  }, [currentProject]);

  const loadSessions = async () => {
    if (!currentProject) return;
    try {
      const list = await api.listQaSessions(currentProject);
      setSessions(list);
    } catch { setSessions([]); }
  };

  // Load messages when session changes
  useEffect(() => {
    if (!activeSession) { setMessages([]); return; }
    api.getSessionMessages(activeSession).then(msgs => {
      setMessages(msgs.map((m: any) => ({ role: m.role, content: m.content })));
    }).catch(() => setMessages([]));
  }, [activeSession]);

  const handleNewSession = async () => {
    if (!currentProject) return;
    try {
      const { id } = await api.createQaSession(currentProject);
      await loadSessions();
      setActiveSession(id);
    } catch {}
  };

  const handleDeleteSession = async (sessionId: number) => {
    try {
      await api.deleteQaSession(sessionId);
      if (activeSession === sessionId) {
        setActiveSession(null);
        setMessages([]);
      }
      loadSessions();
    } catch {}
  };

  const handleSend = async (question: string) => {
    if (!currentProject) return;

    // Auto-create session if none active
    let sessionId = activeSession;
    if (!sessionId) {
      try {
        const { id } = await api.createQaSession(currentProject, question.slice(0, 50));
        sessionId = id;
        setActiveSession(id);
        loadSessions();
      } catch { return; }
    }

    const userMsg: ChatMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setStreamingText('');
    cancelledRef.current = false;

    // Save user message to server
    api.addSessionMessage(sessionId, 'user', question).catch(() => {});

    try {
      const { task_id } = await api.startQa({
        project_name: currentProject,
        question,
        selected_docs: selectedDocs.length > 0 ? selectedDocs : undefined,
      });
      activeTaskRef.current = task_id;

      const currentSessionId = sessionId;

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
          // Save assistant message & update session title
          api.addSessionMessage(currentSessionId, 'assistant', finalText).catch(() => {});
          // Auto-title: update with first user question if it was the first message
          if (messages.length === 0) {
            api.updateQaSession(currentSessionId, question.slice(0, 50)).then(() => loadSessions()).catch(() => {});
          }
        } else if (msg.type === 'error') {
          const errText = `오류: ${msg.error}`;
          setMessages((prev) => [...prev, { role: 'assistant', content: errText }]);
          setStreamingText('');
          setLoading(false);
          unsubscribeTask(task_id);
          api.addSessionMessage(currentSessionId, 'assistant', errText).catch(() => {});
        }
      });

      // Fallback: poll if WebSocket doesn't deliver
      pollRef.current = setInterval(async () => {
        if (cancelledRef.current) { if (pollRef.current) clearInterval(pollRef.current); return; }
        const status = await api.getTaskStatus(task_id);
        if (status.status === 'complete') {
          if (pollRef.current) clearInterval(pollRef.current);
          if (loading) {
            const finalText = status.result || '';
            setMessages((prev) => [...prev, { role: 'assistant', content: finalText }]);
            setStreamingText('');
            setLoading(false);
            api.addSessionMessage(currentSessionId, 'assistant', finalText).catch(() => {});
          }
        } else if (status.status === 'error') {
          if (pollRef.current) clearInterval(pollRef.current);
          if (loading) {
            const errText = `오류: ${status.error}`;
            setMessages((prev) => [...prev, { role: 'assistant', content: errText }]);
            setStreamingText('');
            setLoading(false);
            api.addSessionMessage(currentSessionId, 'assistant', errText).catch(() => {});
          }
        }
      }, 3000);

      setTimeout(() => { if (pollRef.current) clearInterval(pollRef.current); }, 300000);
    } catch (err: any) {
      const errText = `오류: ${err.message}`;
      setMessages((prev) => [...prev, { role: 'assistant', content: errText }]);
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

  if (!currentProject) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <h1 className="text-xl font-bold text-[#37352F] mb-2">자료기반 Q&A</h1>
        <div className="text-sm text-[#9B9A97] py-8 text-center">프로젝트를 먼저 선택하세요.</div>
      </div>
    );
  }

  return (
    <>
      <div className="p-8 pb-28 max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-[#37352F] mb-1">자료기반 Q&A</h1>
            <p className="text-sm text-[#787774]">
              {currentProject} &middot; 문서 {docCount}건 · 선택 {selectedDocs.length}건
            </p>
          </div>
          <button
            onClick={handleNewSession}
            className="px-3 py-1.5 text-sm bg-[#2383E2] text-white rounded-lg hover:bg-[#1b6ec2]"
          >
            + 새 대화
          </button>
        </div>

        <div className="flex gap-4">
          {/* Left sidebar */}
          <div className="w-64 shrink-0 space-y-3">
            {/* Session list */}
            <div className="bg-white border border-[#E9E9E7] rounded-xl p-3 max-h-48 overflow-y-auto">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-semibold text-[#9B9A97] uppercase cursor-pointer"
                  onClick={() => setSessionsOpen(!sessionsOpen)}>
                  대화 목록 {sessionsOpen ? '▾' : '▸'}
                </div>
              </div>
              {sessionsOpen && (
                sessions.length > 0 ? sessions.map(s => (
                  <div key={s.id}
                    className={`flex items-center justify-between px-2 py-1.5 rounded text-xs cursor-pointer mb-0.5 ${activeSession === s.id ? 'bg-[#E8F3FC] text-[#2383E2]' : 'hover:bg-[#F7F6F3] text-[#37352F]'}`}
                    onClick={() => setActiveSession(s.id)}>
                    <span className="truncate flex-1">{s.title}</span>
                    <button onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }}
                      className="text-[#b0b0b0] hover:text-red-500 ml-1 shrink-0">×</button>
                  </div>
                )) : (
                  <div className="text-xs text-[#9B9A97] py-2 text-center">대화 없음</div>
                )
              )}
            </div>

            {/* Document selector */}
            <div className="bg-white border border-[#E9E9E7] rounded-xl p-3 max-h-80 overflow-y-auto">
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
          </div>

          {/* Right: Chat messages */}
          <div className="flex-1">
            <ChatWidget
              messages={messages}
              onSend={handleSend}
              loading={loading}
              onStop={handleStop}
              streamingText={streamingText}
              placeholder="선택한 문서에 대해 질문하세요..."
              externalInput
            />
          </div>
        </div>
      </div>

      {/* Floating bottom input bar */}
      <div className="sticky bottom-0 z-10 border-t border-[#E9E9E7] bg-white/95 backdrop-blur-sm shadow-[0_-4px_16px_rgba(0,0,0,0.06)]">
        <div className="max-w-5xl mx-auto px-8 py-4">
          <ChatInputBar
            onSend={handleSend}
            loading={loading}
            onStop={handleStop}
            placeholder="선택한 문서에 대해 질문하세요..."
          />
        </div>
      </div>
    </>
  );
}
