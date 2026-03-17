/**
 * OutlineEditor — AI 생성 아웃라인 편집 UI
 * 섹션/슬라이드 추가, 삭제, 이름 변경, 순서 변경 지원
 */
import { useState, useCallback } from 'react';

interface SlidePlan {
  title: string;
  slide_type?: string;
  plan?: string;
}

interface Section {
  title: string;
  slides: SlidePlan[];
}

interface Outline {
  sections: Section[];
}

interface Props {
  outline: Outline;
  onConfirm: (editedOutline: Outline) => void;
  onCancel: () => void;
}

export default function OutlineEditor({ outline, onConfirm, onCancel }: Props) {
  const [sections, setSections] = useState<Section[]>(
    () => JSON.parse(JSON.stringify(outline.sections || []))
  );

  const updateSection = useCallback((secIdx: number, updates: Partial<Section>) => {
    setSections(prev => prev.map((s, i) => i === secIdx ? { ...s, ...updates } : s));
  }, []);

  const removeSection = useCallback((secIdx: number) => {
    setSections(prev => prev.filter((_, i) => i !== secIdx));
  }, []);

  const addSection = useCallback(() => {
    setSections(prev => [...prev, { title: '새 섹션', slides: [{ title: '새 슬라이드', slide_type: 'two_column' }] }]);
  }, []);

  const moveSection = useCallback((secIdx: number, dir: -1 | 1) => {
    setSections(prev => {
      const arr = [...prev];
      const newIdx = secIdx + dir;
      if (newIdx < 0 || newIdx >= arr.length) return arr;
      [arr[secIdx], arr[newIdx]] = [arr[newIdx], arr[secIdx]];
      return arr;
    });
  }, []);

  const updateSlide = useCallback((secIdx: number, slideIdx: number, updates: Partial<SlidePlan>) => {
    setSections(prev => prev.map((s, si) => si !== secIdx ? s : {
      ...s,
      slides: s.slides.map((sl, sli) => sli === slideIdx ? { ...sl, ...updates } : sl),
    }));
  }, []);

  const removeSlide = useCallback((secIdx: number, slideIdx: number) => {
    setSections(prev => prev.map((s, si) => si !== secIdx ? s : {
      ...s,
      slides: s.slides.filter((_, i) => i !== slideIdx),
    }));
  }, []);

  const addSlide = useCallback((secIdx: number) => {
    setSections(prev => prev.map((s, si) => si !== secIdx ? s : {
      ...s,
      slides: [...s.slides, { title: '새 슬라이드', slide_type: 'two_column' }],
    }));
  }, []);

  const moveSlide = useCallback((secIdx: number, slideIdx: number, dir: -1 | 1) => {
    setSections(prev => prev.map((s, si) => {
      if (si !== secIdx) return s;
      const arr = [...s.slides];
      const newIdx = slideIdx + dir;
      if (newIdx < 0 || newIdx >= arr.length) return s;
      [arr[slideIdx], arr[newIdx]] = [arr[newIdx], arr[newIdx]];
      [arr[slideIdx], arr[newIdx]] = [arr[newIdx], arr[slideIdx]];
      return { ...s, slides: arr };
    }));
  }, []);

  const totalSlides = sections.reduce((sum, s) => sum + s.slides.length, 0);

  return (
    <div className="bg-white border border-[#E9E9E7] rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-sm font-semibold text-[#37352F]">아웃라인 편집</div>
          <div className="text-xs text-[#787774]">
            {sections.length}개 섹션, {totalSlides}개 슬라이드
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={onCancel}
            className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3]">
            취소
          </button>
          <button onClick={() => onConfirm({ sections })}
            className="px-4 py-1.5 text-xs bg-[#2383E2] text-white rounded-lg hover:bg-[#1b6ec2]">
            이 아웃라인으로 생성
          </button>
        </div>
      </div>

      <div className="space-y-3 max-h-[500px] overflow-y-auto">
        {sections.map((section, secIdx) => (
          <div key={secIdx} className="border border-[#E9E9E7] rounded-lg p-3">
            {/* Section header */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-bold text-[#787774] w-6">{secIdx + 1}.</span>
              <input
                value={section.title}
                onChange={(e) => updateSection(secIdx, { title: e.target.value })}
                className="flex-1 px-2 py-1 text-sm font-semibold text-[#37352F] border border-transparent hover:border-[#E9E9E7] focus:border-[#2383E2] rounded focus:outline-none"
              />
              <button onClick={() => moveSection(secIdx, -1)} disabled={secIdx === 0}
                className="p-1 text-xs text-[#787774] hover:text-[#37352F] disabled:opacity-30" title="위로">
                &#9650;
              </button>
              <button onClick={() => moveSection(secIdx, 1)} disabled={secIdx === sections.length - 1}
                className="p-1 text-xs text-[#787774] hover:text-[#37352F] disabled:opacity-30" title="아래로">
                &#9660;
              </button>
              <button onClick={() => removeSection(secIdx)}
                className="p-1 text-xs text-red-400 hover:text-red-600" title="섹션 삭제">
                &#10005;
              </button>
            </div>

            {/* Slides in section */}
            <div className="ml-6 space-y-1">
              {section.slides.map((slide, slideIdx) => (
                <div key={slideIdx} className="flex items-center gap-2 group">
                  <span className="text-[10px] text-[#787774] w-4">{slideIdx + 1}</span>
                  <input
                    value={slide.title}
                    onChange={(e) => updateSlide(secIdx, slideIdx, { title: e.target.value })}
                    className="flex-1 px-2 py-0.5 text-xs text-[#37352F] border border-transparent hover:border-[#E9E9E7] focus:border-[#2383E2] rounded focus:outline-none"
                  />
                  <select
                    value={slide.slide_type || 'two_column'}
                    onChange={(e) => updateSlide(secIdx, slideIdx, { slide_type: e.target.value })}
                    className="text-[10px] text-[#787774] border border-[#E9E9E7] rounded px-1 py-0.5"
                  >
                    <option value="data_table">data_table</option>
                    <option value="chart_table">chart_table</option>
                    <option value="two_column">two_column</option>
                    <option value="kpi_dashboard">kpi_dashboard</option>
                    <option value="risk_matrix">risk_matrix</option>
                    <option value="timeline_flow">timeline_flow</option>
                    <option value="comparison">comparison</option>
                    <option value="numbered_blocks">numbered_blocks</option>
                    <option value="grid_cards">grid_cards</option>
                  </select>
                  <button onClick={() => moveSlide(secIdx, slideIdx, -1)} disabled={slideIdx === 0}
                    className="p-0.5 text-[10px] text-[#787774] opacity-0 group-hover:opacity-100 disabled:opacity-0">
                    &#9650;
                  </button>
                  <button onClick={() => moveSlide(secIdx, slideIdx, 1)} disabled={slideIdx === section.slides.length - 1}
                    className="p-0.5 text-[10px] text-[#787774] opacity-0 group-hover:opacity-100 disabled:opacity-0">
                    &#9660;
                  </button>
                  <button onClick={() => removeSlide(secIdx, slideIdx)}
                    className="p-0.5 text-[10px] text-red-400 opacity-0 group-hover:opacity-100 hover:text-red-600">
                    &#10005;
                  </button>
                </div>
              ))}
              <button onClick={() => addSlide(secIdx)}
                className="text-[10px] text-[#2383E2] hover:underline ml-4">
                + 슬라이드 추가
              </button>
            </div>
          </div>
        ))}
      </div>

      <button onClick={addSection}
        className="mt-3 w-full py-1.5 text-xs text-[#2383E2] border border-dashed border-[#2383E2] rounded-lg hover:bg-[#EFF6FF]">
        + 섹션 추가
      </button>
    </div>
  );
}
