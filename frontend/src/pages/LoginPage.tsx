import { useState } from 'react';
import { api } from '../api/client';
import { useAuthStore } from '../stores/authStore';

export default function LoginPage() {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result =
        tab === 'login'
          ? await api.login(username, password)
          : await api.register(username, password, inviteCode);
      setAuth(result.token, result.user);
    } catch (err: any) {
      const msg = err?.message || '';
      if (msg.includes('401')) setError('아이디 또는 비밀번호가 올바르지 않습니다.');
      else if (msg.includes('400')) setError('유효하지 않거나 사용된 초대코드입니다.');
      else if (msg.includes('409')) setError('이미 존재하는 사용자명입니다.');
      else setError(msg || '오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center"
      style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)' }}>
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-3"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}>
            <span className="text-2xl">💎</span>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">GEM Intern</h1>
          <p className="text-sm text-slate-500 mt-1">AI-Powered Investment Analysis</p>
        </div>

        {/* Card */}
        <div className="bg-white/[0.05] backdrop-blur border border-white/[0.1] rounded-2xl p-6">
          {/* Tabs */}
          <div className="flex mb-6 bg-white/[0.05] rounded-lg p-1">
            <button
              onClick={() => { setTab('login'); setError(''); }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                tab === 'login'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              로그인
            </button>
            <button
              onClick={() => { setTab('register'); setError(''); }}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                tab === 'register'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              회원가입
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {tab === 'register' && (
              <div>
                <label className="block text-xs text-slate-400 mb-1.5">초대 코드</label>
                <input
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder="관리자에게 받은 초대 코드"
                  required
                  className="w-full px-3 py-2.5 bg-white/[0.06] border border-white/[0.1] rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors"
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">사용자명</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                required
                autoFocus
                className="w-full px-3 py-2.5 bg-white/[0.06] border border-white/[0.1] rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">비밀번호</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
                className="w-full px-3 py-2.5 bg-white/[0.06] border border-white/[0.1] rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors"
              />
            </div>

            {error && (
              <div className="px-3 py-2 rounded-lg text-xs text-red-400 bg-red-500/10 border border-red-500/20">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-all disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}
            >
              {loading ? '...' : tab === 'login' ? '로그인' : '가입하기'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
