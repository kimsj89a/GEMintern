import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAppStore } from '../stores/appStore';

const MODELS = [
  'gemini-3.1-pro-preview',
  'gemini-3-pro-preview',
  'gemini-3-flash-preview',
  'gemini-2.5-flash',
  'gemini-2.5-pro',
  'gemini-2.0-flash',
];

const THINKING_LEVELS = ['MINIMAL', 'LOW', 'MEDIUM', 'HIGH'];

export default function SettingsPage() {
  const { setAppStarted, openTab } = useAppStore();
  const [model, setModel] = useState(MODELS[0]);
  const [thinking, setThinking] = useState('MEDIUM');
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
  const [status, setStatus] = useState<{ type: string; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const [gdriveEnabled, setGdriveEnabled] = useState(false);
  const [gdriveClientId, setGdriveClientId] = useState('');
  const [gdriveClientSecret, setGdriveClientSecret] = useState('');
  const [gdriveJsonName, setGdriveJsonName] = useState('');

  useEffect(() => {
    api.getSettings().then((data) => {
      if (data.model_name) setModel(data.model_name);
      if (data.thinking_level) setThinking(data.thinking_level);
      setApiKeyConfigured(!!data.api_key_configured);
      const cs = data.cloud_sync || {};
      if (cs.gdrive_enabled) setGdriveEnabled(true);
      if (cs.gdrive_client_id) setGdriveClientId(cs.gdrive_client_id);
      if (cs.gdrive_client_secret) setGdriveClientSecret(cs.gdrive_client_secret);
    }).catch(() => {});
  }, []);

  const handleJsonUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result as string);
        const installed = data.installed || data.web || data;
        if (installed.client_id) {
          setGdriveClientId(installed.client_id);
          setGdriveClientSecret(installed.client_secret || '');
          setGdriveJsonName(file.name);
        } else {
          setStatus({ type: 'error', msg: 'JSON에서 client_id를 찾을 수 없습니다.' });
        }
      } catch {
        setStatus({ type: 'error', msg: 'JSON 파싱 오류' });
      }
    };
    reader.readAsText(file);
  };

  const handleApply = async () => {
    setLoading(true);
    setStatus(null);
    try {
      await api.updateSettings({
        model_name: model,
        thinking_level: thinking,
        cloud_sync: {
          gdrive_enabled: gdriveEnabled,
          gdrive_client_id: gdriveClientId,
          gdrive_client_secret: gdriveClientSecret,
        },
      });
      const result = await api.applySettings();
      if (result.success) {
        setStatus({ type: 'success', msg: '설정이 적용되었습니다!' });
        setAppStarted(true);
        setTimeout(() => openTab('home'), 500);
      } else {
        setStatus({ type: 'error', msg: result.error || '설정 적용 실패' });
      }
    } catch (err: any) {
      setStatus({ type: 'error', msg: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">⚙️ 설정</h1>
      <p className="text-sm text-[#787774] mb-6">API 키와 모델을 설정하고 업무를 시작합니다.</p>

      {status && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${
          status.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {status.msg}
        </div>
      )}

      {/* API Settings */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-6 mb-4">
        <h2 className="text-sm font-semibold text-[#37352F] mb-4">Gemini API</h2>

        <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-[#F7F6F3] rounded-lg">
          <div className={`w-2 h-2 rounded-full ${apiKeyConfigured ? 'bg-emerald-500' : 'bg-red-400'}`} />
          <span className="text-sm text-[#787774]">
            API Key: {apiKeyConfigured ? '서버 환경변수에서 설정됨' : '미설정 (GEMINI_API_KEY 환경변수 필요)'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-[#787774] mb-1">모델</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]"
            >
              {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm text-[#787774] mb-1">Thinking Level</label>
            <select
              value={thinking}
              onChange={(e) => setThinking(e.target.value)}
              className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]"
            >
              {THINKING_LEVELS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Cloud Sync */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-6 mb-6">
        <h2 className="text-sm font-semibold text-[#37352F] mb-4">클라우드 연동</h2>

        <label className="flex items-center gap-2 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={gdriveEnabled}
            onChange={(e) => setGdriveEnabled(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm text-[#37352F]">Google Drive 동기화 사용</span>
        </label>

        {gdriveEnabled && (
          <div className="space-y-3 pl-6 border-l-2 border-[#E9E9E7]">
            <div>
              <label className="block text-sm text-[#787774] mb-1">인증 JSON</label>
              <div className="flex items-center gap-2">
                <label className="px-3 py-1.5 text-sm border border-[#E9E9E7] rounded-lg cursor-pointer hover:bg-[#F7F6F3] transition-colors">
                  📂 credentials.json 업로드
                  <input type="file" accept=".json" onChange={handleJsonUpload} className="hidden" />
                </label>
                {gdriveJsonName && <span className="text-xs text-green-600">✅ {gdriveJsonName}</span>}
              </div>
            </div>
            <div>
              <label className="block text-sm text-[#787774] mb-1">Client ID</label>
              <input type="text" value={gdriveClientId} onChange={(e) => setGdriveClientId(e.target.value)}
                placeholder="Google OAuth Client ID"
                className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]" />
            </div>
            <div>
              <label className="block text-sm text-[#787774] mb-1">Client Secret</label>
              <input type="password" value={gdriveClientSecret} onChange={(e) => setGdriveClientSecret(e.target.value)}
                placeholder="Google OAuth Client Secret"
                className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2]" />
            </div>
          </div>
        )}
      </div>

      <button
        onClick={handleApply}
        disabled={loading}
        className="w-full py-3 bg-[#2383E2] text-white font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors text-sm"
      >
        {loading ? '적용 중...' : '✅ 설정 적용 및 업무 시작'}
      </button>
    </div>
  );
}
