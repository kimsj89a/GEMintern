import { useAuthStore } from '../stores/authStore';

type WsMessage = {
  type: 'chunk' | 'slide' | 'complete' | 'error';
  task_id: string;
  data?: string;
  slide?: any;
  index?: number;
  result?: string;
  error?: string;
};

type WsCallback = (msg: WsMessage) => void;

let ws: WebSocket | null = null;
const listeners = new Map<string, WsCallback>();

function getWs(): WebSocket {
  if (ws && ws.readyState === WebSocket.OPEN) return ws;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = useAuthStore.getState().token || '';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/stream?token=${encodeURIComponent(token)}`);

  ws.onmessage = (event) => {
    const raw = JSON.parse(event.data);
    let msg: WsMessage = raw;

    // Handle slide streaming: chunks contain JSON-encoded slide messages
    if (raw.type === 'chunk' && raw.data) {
      try {
        const parsed = JSON.parse(raw.data);
        if (parsed.type === 'slide' && parsed.slide) {
          msg = {
            type: 'slide',
            task_id: raw.task_id,
            slide: parsed.slide,
            index: parsed.index,
          };
        }
      } catch {
        // Regular text chunk, pass through
      }
    }

    const cb = listeners.get(msg.task_id);
    if (cb) cb(msg);
  };

  ws.onclose = () => {
    ws = null;
  };

  return ws;
}

export function subscribeTask(taskId: string, callback: WsCallback) {
  listeners.set(taskId, callback);
  const socket = getWs();
  const send = () =>
    socket.send(JSON.stringify({ type: 'subscribe', task_id: taskId }));
  if (socket.readyState === WebSocket.OPEN) {
    send();
  } else {
    socket.addEventListener('open', send, { once: true });
  }
}

export function unsubscribeTask(taskId: string) {
  listeners.delete(taskId);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'unsubscribe', task_id: taskId }));
  }
}
