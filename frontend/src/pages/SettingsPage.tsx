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
  'claude-opus-4-7',
  'claude-sonnet-4-6',
  'gpt-5.5-2026-04-23',
];

const THINKING_LEVELS = ['MINIMAL', 'LOW', 'MEDIUM', 'HIGH'];

export default function SettingsPage() {
  const { setAppStarted, openTab } = useAppStore();
  const [model, setModel] = useState(MODELS[0]);
  const [thinking, setThinking] = useState('MEDIUM');
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
  const [anthropicKeyConfigured, setAnthropicKeyConfigured] = useState(false);
  const [openaiKeyConfigured, setOpenaiKeyConfigured] = useState(false);
  const [status, setStatus] = useState<{ type: string; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const isClaude = model.startsWith('claude-');
  const isGpt = model.startsWith('gpt-');

  useEffect(() => {
    api.getSettings().then((data) => {
      if (data.model_name) setModel(data.model_name);
      if (data.thinking_level) setThinking(data.thinking_level);
      setApiKeyConfigured(!!data.api_key_configured);
      setAnthropicKeyConfigured(!!data.anthropic_api_key_configured);
      setOpenaiKeyConfigured(!!data.openai_api_key_configured);
    }).catch(() => {});
  }, []);

  const handleApply = async () => {
    setLoading(true);
    setStatus(null);
    try {
      await api.updateSettings({
        model_name: model,
        thinking_level: thinking,
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
        <h2 className="text-sm font-semibold text-[#37352F] mb-4">AI API 설정</h2>

        <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-[#F7F6F3] rounded-lg">
          <div className={`w-2 h-2 rounded-full ${apiKeyConfigured ? 'bg-emerald-500' : 'bg-red-400'}`} />
          <span className="text-sm text-[#787774]">
            Gemini API Key: {apiKeyConfigured ? '설정됨' : '미설정 (GEMINI_API_KEY 환경변수 필요)'}
          </span>
        </div>

        <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-[#F7F6F3] rounded-lg">
          <div className={`w-2 h-2 rounded-full ${anthropicKeyConfigured ? 'bg-emerald-500' : 'bg-amber-400'}`} />
          <span className="text-sm text-[#787774]">
            Anthropic API Key: {anthropicKeyConfigured ? '설정됨' : '미설정 (Claude 모델 사용 시 필요)'}
          </span>
        </div>

        <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-[#F7F6F3] rounded-lg">
          <div className={`w-2 h-2 rounded-full ${openaiKeyConfigured ? 'bg-emerald-500' : 'bg-amber-400'}`} />
          <span className="text-sm text-[#787774]">
            OpenAI API Key: {openaiKeyConfigured ? '설정됨' : '미설정 (GPT 모델 사용 시 필요)'}
          </span>
        </div>

        {isClaude && !anthropicKeyConfigured && (
          <div className="mb-4 px-4 py-3 rounded-lg text-sm bg-amber-50 text-amber-700 border border-amber-200">
            Claude 모델을 사용하려면 .env 파일에 ANTHROPIC_API_KEY를 설정해주세요.
          </div>
        )}

        {isGpt && !openaiKeyConfigured && (
          <div className="mb-4 px-4 py-3 rounded-lg text-sm bg-amber-50 text-amber-700 border border-amber-200">
            GPT 모델을 사용하려면 .env 파일에 OPENAI_API_KEY를 설정해주세요.
          </div>
        )}

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
