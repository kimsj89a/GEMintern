import { useEffect, useState } from 'react';

interface GenerationProgressProps {
  streamingText: string;
  startTime: number;
  onStop: () => void;
}

function extractSections(text: string): string[] {
  const sections: string[] = [];
  for (const line of text.split('\n')) {
    const m = line.match(/^(#{1,3})\s+(.+)/);
    if (m) {
      const level = m[1].length;
      const title = m[2].trim();
      if (title) sections.push(`${'#'.repeat(level)} ${title}`);
    }
  }
  return sections;
}

function formatElapsed(ms: number): string {
  const sec = Math.floor(ms / 1000);
  const min = Math.floor(sec / 60);
  const s = sec % 60;
  if (min > 0) return `${min}분 ${s}초`;
  return `${s}초`;
}

export default function GenerationProgress({ streamingText, startTime, onStop }: GenerationProgressProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(Date.now() - startTime);
    }, 1000);
    return () => clearInterval(timer);
  }, [startTime]);

  const charCount = streamingText.length;
  const sections = extractSections(streamingText);
  const currentSection = sections.length > 0 ? sections[sections.length - 1] : null;
  const estimatedTotal = 15000;
  const progressPct = Math.min(95, Math.round((charCount / estimatedTotal) * 100));

  return (
    <div className="mb-5 space-y-3 animate-fade-in-up">
      {/* Top row */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5 flex-1">
          <div className="w-2.5 h-2.5 rounded-full gradient-accent" style={{ animation: 'pulse-soft 1.5s ease infinite' }} />
          <span className="text-sm font-semibold text-slate-700">문서 생성 중</span>
        </div>
        <button onClick={onStop}
          className="px-4 py-1.5 bg-red-500 text-white text-xs font-semibold rounded-lg hover:bg-red-600 transition-all hover:shadow-md active:scale-[0.97]">
          중지
        </button>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
        <div
          className="progress-gradient h-2 rounded-full transition-[width] duration-700 ease-out"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-5 text-xs">
        <div className="flex items-center gap-1.5 text-slate-500">
          <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/><path d="M8 4v4l3 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          <span>{formatElapsed(elapsed)}</span>
        </div>
        <div className="flex items-center gap-1.5 text-slate-500">
          <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none"><path d="M3 3h10v10H3z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M5 7h6M5 10h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          <span><span className="font-medium text-slate-700">{charCount.toLocaleString()}</span>자</span>
        </div>
        <div className="flex items-center gap-1.5 text-slate-500">
          <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          <span><span className="font-medium text-slate-700">{sections.length}</span>개 섹션</span>
        </div>
      </div>

      {/* Current section */}
      {currentSection && (
        <div className="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
          <span className="text-xs text-blue-600 font-medium">{currentSection.replace(/^#+\s*/, '')}</span>
        </div>
      )}

      {/* Section list */}
      {sections.length > 1 && (
        <details className="text-xs group">
          <summary className="cursor-pointer text-slate-400 hover:text-slate-600 transition-colors font-medium">
            완료된 섹션 ({sections.length - 1}개)
          </summary>
          <div className="mt-2 pl-3 border-l-2 border-slate-200 space-y-1">
            {sections.slice(0, -1).map((s, i) => {
              const level = (s.match(/^#+/) || [''])[0].length;
              return (
                <div key={i} className="flex items-center gap-1.5" style={{ paddingLeft: `${(level - 1) * 12}px` }}>
                  <svg className="w-3 h-3 text-emerald-500" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" fill="currentColor" fillOpacity="0.15"/><path d="M5.5 8l2 2 3.5-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  <span className="text-slate-600">{s.replace(/^#+\s*/, '')}</span>
                </div>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}
