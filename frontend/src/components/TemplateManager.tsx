/**
 * TemplateManager — 노트 템플릿 CRUD 모달.
 * 전역 템플릿(scope=global)은 읽기 전용, 사용자 템플릿(scope=user)은 편집/삭제 가능.
 */
import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface NoteTemplate { name: string; scope: 'global' | 'user'; editable: boolean; body?: string; }

interface Props {
  projectName: string;
  templates: NoteTemplate[];
  onClose: () => void;
  onChanged: () => void;
}

export default function TemplateManager({ projectName, templates, onClose, onChanged }: Props) {
  const [activeName, setActiveName] = useState<string | null>(null);
  const [activeBody, setActiveBody] = useState('');
  const [activeScope, setActiveScope] = useState<'global' | 'user'>('user');
  const [draftName, setDraftName] = useState('');
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);

  // 첫 진입 시 자동 첫 항목 선택
  useEffect(() => {
    if (templates.length > 0 && !activeName && !creating) {
      void selectTemplate(templates[0].name);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templates]);

  const selectTemplate = async (name: string) => {
    setCreating(false);
    try {
      const t = await api.getNoteTemplate(projectName, name);
      setActiveName(t.name);
      setActiveBody(t.body || '');
      setActiveScope(t.scope);
      setDraftName(t.name);
    } catch {}
  };

  const startNew = () => {
    setCreating(true);
    setActiveName(null);
    setActiveBody('# ${title}\n\n- 일자: ${date}\n\n## 메모\n- \n');
    setActiveScope('user');
    setDraftName('');
  };

  const save = async () => {
    const name = draftName.trim();
    if (!name) { alert('템플릿 이름을 입력하세요.'); return; }
    setSaving(true);
    try {
      await api.upsertNoteTemplate(projectName, name, activeBody);
      onChanged();
      setCreating(false);
      setActiveName(name);
    } catch (e: any) { alert(`저장 실패: ${e?.message || e}`); }
    finally { setSaving(false); }
  };

  const remove = async () => {
    if (!activeName) return;
    if (!confirm(`사용자 템플릿 "${activeName}"을(를) 삭제할까요?`)) return;
    try {
      await api.deleteNoteTemplate(projectName, activeName);
      onChanged();
      setActiveName(null);
      setActiveBody('');
      setDraftName('');
    } catch (e: any) { alert(`삭제 실패: ${e?.message || e}`); }
  };

  const isReadOnly = activeScope === 'global' && !creating;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-[820px] max-w-[95vw] h-[600px] max-h-[85vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-700">⚙ 노트 템플릿 관리</div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg">✕</button>
        </div>

        {/* Body: list + editor */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: template list */}
          <div className="w-56 shrink-0 border-r border-slate-200 flex flex-col bg-slate-50/30">
            <div className="p-2 border-b border-slate-200">
              <button onClick={startNew}
                className="w-full px-2 py-1.5 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">+ 새 템플릿</button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {templates.map(t => {
                const active = !creating && activeName === t.name;
                return (
                  <button key={`${t.scope}-${t.name}`}
                    onClick={() => selectTemplate(t.name)}
                    className={`w-full text-left px-3 py-2 border-b border-slate-100 text-xs flex items-center gap-1.5 ${
                      active ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-slate-100 text-slate-700'
                    }`}>
                    <span className="text-slate-400 shrink-0">{t.scope === 'global' ? '📋' : '⭐'}</span>
                    <span className="truncate">{t.name}</span>
                    {t.scope === 'global' && <span className="ml-auto text-[9px] text-slate-400">기본</span>}
                  </button>
                );
              })}
              {templates.length === 0 && (
                <div className="px-3 py-4 text-xs text-slate-400 text-center">템플릿 없음</div>
              )}
            </div>
            <div className="p-2 text-[10px] text-slate-400 border-t border-slate-200">
              📋 기본(읽기전용) · ⭐ 사용자 정의
            </div>
          </div>

          {/* Right: editor */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {(activeName || creating) ? (
              <>
                <div className="px-4 py-2.5 border-b border-slate-200 flex items-center gap-2">
                  <input value={draftName}
                    onChange={e => setDraftName(e.target.value)}
                    disabled={isReadOnly}
                    placeholder="템플릿 이름 (예: 미팅로그)"
                    className="flex-1 px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-400 disabled:bg-slate-50 disabled:text-slate-400" />
                  {isReadOnly ? (
                    <span className="text-[10px] text-slate-500 px-2">읽기 전용 · 복사해 사용자 템플릿으로 만드세요</span>
                  ) : (
                    <>
                      <button onClick={save} disabled={saving || !draftName.trim()}
                        className="px-3 py-1.5 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50">
                        {saving ? '저장중…' : '저장'}
                      </button>
                      {!creating && activeScope === 'user' && (
                        <button onClick={remove}
                          className="px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded-lg hover:bg-red-50">삭제</button>
                      )}
                    </>
                  )}
                </div>
                <div className="px-4 py-2 bg-amber-50/40 border-b border-amber-100 text-[11px] text-amber-700">
                  변수: <code>${'${date}'}</code> · <code>${'${time}'}</code> · <code>${'${title}'}</code> · <code>${'${project}'}</code>
                </div>
                <textarea value={activeBody}
                  onChange={e => setActiveBody(e.target.value)}
                  readOnly={isReadOnly}
                  placeholder="템플릿 본문 (마크다운)"
                  className="flex-1 px-4 py-3 text-[13px] leading-relaxed font-mono outline-none resize-none read-only:bg-slate-50 read-only:text-slate-600" />
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-sm text-slate-400">
                좌측에서 템플릿을 선택하거나 "+ 새 템플릿"을 만드세요
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
