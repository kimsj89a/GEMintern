/**
 * SlidePreview — SVG-based schematic preview of a single slide.
 * Renders atomic elements (text_box, shape, chart, callout, icon) as simplified visuals.
 */
import { useMemo } from 'react';

// Layout constants (10:7.5 ratio scaled to viewBox 400x300)
const VB_W = 400;
const VB_H = 300;
const PAD = 12;
const HEADER_H = 20;
const TITLE_H = 24;
const CX = PAD;
const CY = HEADER_H + TITLE_H + 4;
const CW = VB_W - PAD * 2;
const CH = VB_H - CY - PAD;

interface SlideData {
  slide_type?: string;
  type?: string; // legacy
  title?: string;
  subtitle?: string;
  layout_hint?: string;
  elements?: any[];
  // legacy
  left?: any;
  right?: any;
}

interface Props {
  slide: SlideData;
  selected?: boolean;
  onClick?: () => void;
  width?: number;
}

// Color palette
const BLUE = '#1E3A8A';
const LIGHT_BLUE = '#DBEAFE';
const ACCENT = '#2383E2';
const GREY = '#F7F6F3';
const DARK = '#37352F';

function computeLayout(elements: any[], hint: string) {
  if (!elements?.length) return [];
  const n = elements.length;

  const positioned = elements.map((el: any, i: number) => ({ ...el, _idx: i }));

  switch (hint) {
    case 'single_column': {
      const h = CH / n;
      return positioned.map((el: any, i: number) => ({
        ...el, _x: CX, _y: CY + i * h, _w: CW, _h: h - 2,
      }));
    }
    case 'two_column': {
      const half = Math.ceil(n / 2);
      return positioned.map((el: any, i: number) => {
        const col = i < half ? 0 : 1;
        const row = col === 0 ? i : i - half;
        const rows = col === 0 ? half : n - half;
        const h = CH / Math.max(rows, 1);
        return {
          ...el,
          _x: CX + col * (CW / 2 + 2),
          _y: CY + row * h,
          _w: CW / 2 - 2,
          _h: h - 2,
        };
      });
    }
    case 'three_column': {
      const perCol = Math.ceil(n / 3);
      return positioned.map((el: any, i: number) => {
        const col = Math.min(Math.floor(i / perCol), 2);
        const row = i - col * perCol;
        const colW = CW / 3 - 2;
        const h = CH / Math.max(perCol, 1);
        return { ...el, _x: CX + col * (colW + 3), _y: CY + row * h, _w: colW, _h: h - 2 };
      });
    }
    case 'kpi_row': {
      const callouts = positioned.filter((e: any) => e.kind === 'callout');
      const rest = positioned.filter((e: any) => e.kind !== 'callout');
      const kpiH = CH * 0.35;
      const kpiW = CW / Math.max(callouts.length, 1) - 2;
      const result = callouts.map((el: any, i: number) => ({
        ...el, _x: CX + i * (kpiW + 2), _y: CY, _w: kpiW, _h: kpiH - 2,
      }));
      const restH = (CH - kpiH) / Math.max(rest.length, 1);
      rest.forEach((el: any, i: number) => {
        result.push({ ...el, _x: CX, _y: CY + kpiH + i * restH, _w: CW, _h: restH - 2 });
      });
      return result;
    }
    case 'chart_with_text': {
      const charts = positioned.filter((e: any) => e.kind === 'chart');
      const texts = positioned.filter((e: any) => e.kind !== 'chart');
      const chartW = CW * 0.6;
      const result = charts.map((el: any, i: number) => ({
        ...el, _x: CX, _y: CY + i * (CH / Math.max(charts.length, 1)),
        _w: chartW - 2, _h: CH / Math.max(charts.length, 1) - 2,
      }));
      const tH = CH / Math.max(texts.length, 1);
      texts.forEach((el: any, i: number) => {
        result.push({ ...el, _x: CX + chartW + 2, _y: CY + i * tH, _w: CW - chartW - 2, _h: tH - 2 });
      });
      return result;
    }
    case 'text_with_chart': {
      const charts = positioned.filter((e: any) => e.kind === 'chart');
      const texts = positioned.filter((e: any) => e.kind !== 'chart');
      const textW = CW * 0.4;
      const tH = CH / Math.max(texts.length, 1);
      const result = texts.map((el: any, i: number) => ({
        ...el, _x: CX, _y: CY + i * tH, _w: textW - 2, _h: tH - 2,
      }));
      charts.forEach((el: any, i: number) => {
        result.push({
          ...el, _x: CX + textW + 2, _y: CY + i * (CH / Math.max(charts.length, 1)),
          _w: CW - textW - 2, _h: CH / Math.max(charts.length, 1) - 2,
        });
      });
      return result;
    }
    case 'process_flow':
    case 'timeline': {
      const w = CW / n - 4;
      return positioned.map((el: any, i: number) => ({
        ...el, _x: CX + i * (w + 4), _y: CY + CH * 0.2, _w: w, _h: CH * 0.6,
      }));
    }
    case 'quote': {
      return positioned.map((el: any) => ({
        ...el, _x: CX + CW * 0.1, _y: CY + CH * 0.2, _w: CW * 0.8, _h: CH * 0.6,
      }));
    }
    case 'grid': {
      const cols = Math.ceil(Math.sqrt(n));
      const rows = Math.ceil(n / cols);
      const cellW = CW / cols - 2;
      const cellH = CH / rows - 2;
      return positioned.map((el: any, i: number) => ({
        ...el,
        _x: CX + (i % cols) * (cellW + 2),
        _y: CY + Math.floor(i / cols) * (cellH + 2),
        _w: cellW, _h: cellH,
      }));
    }
    default: { // auto / full_image
      const h = CH / n;
      return positioned.map((el: any, i: number) => ({
        ...el, _x: CX, _y: CY + i * h, _w: CW, _h: h - 2,
      }));
    }
  }
}

function truncate(text: string, maxLen: number) {
  if (!text) return '';
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
}

function ElementRect({ el }: { el: any }) {
  const { _x, _y, _w, _h, kind } = el;
  if (_w < 2 || _h < 2) return null;

  const fontSize = Math.min(7, _h * 0.25);

  if (kind === 'chart') {
    return (
      <g>
        <rect x={_x} y={_y} width={_w} height={_h} fill={LIGHT_BLUE} stroke={ACCENT} strokeWidth={0.5} rx={2} />
        {/* Symbolic bars */}
        {[0.2, 0.4, 0.6, 0.8].map((pct, i) => {
          const bh = _h * (0.3 + Math.random() * 0.4);
          return (
            <rect key={i} x={_x + _w * pct - _w * 0.06} y={_y + _h - bh - 4}
              width={_w * 0.12} height={bh} fill={ACCENT} opacity={0.6 + i * 0.1} rx={1} />
          );
        })}
        <text x={_x + _w / 2} y={_y + 8} textAnchor="middle" fontSize={5} fill={DARK}>
          {truncate(el.chart_type || 'chart', 15)}
        </text>
      </g>
    );
  }

  if (kind === 'callout') {
    return (
      <g>
        <rect x={_x} y={_y} width={_w} height={_h} fill="#F0F7FF" stroke={ACCENT} strokeWidth={0.8} rx={3} />
        <text x={_x + _w / 2} y={_y + _h * 0.4} textAnchor="middle" fontSize={Math.min(10, _h * 0.3)} fontWeight="bold" fill={ACCENT}>
          {truncate(el.value || '', 10)}
        </text>
        <text x={_x + _w / 2} y={_y + _h * 0.65} textAnchor="middle" fontSize={fontSize} fill={DARK}>
          {truncate(el.label || '', 15)}
        </text>
        {el.delta && (
          <text x={_x + _w / 2} y={_y + _h * 0.85} textAnchor="middle" fontSize={fontSize * 0.85} fill="#16A34A">
            {truncate(el.delta, 12)}
          </text>
        )}
      </g>
    );
  }

  if (kind === 'shape') {
    const fill = el.fill || LIGHT_BLUE;
    if (el.shape_type === 'circle' || el.shape_type === 'oval') {
      const cx = _x + _w / 2;
      const cy = _y + _h / 2;
      const r = Math.min(_w, _h) / 2 - 1;
      return (
        <g>
          <ellipse cx={cx} cy={cy} rx={r} ry={r} fill={fill} stroke={ACCENT} strokeWidth={0.5} />
          <text x={cx} y={cy + 2} textAnchor="middle" fontSize={fontSize} fill={DARK}>
            {truncate(el.text || '', 12)}
          </text>
        </g>
      );
    }
    return (
      <g>
        <rect x={_x} y={_y} width={_w} height={_h} fill={fill} stroke={ACCENT} strokeWidth={0.5} rx={el.shape_type?.includes('round') ? 4 : 1} />
        <text x={_x + _w / 2} y={_y + _h / 2 + 2} textAnchor="middle" fontSize={fontSize} fill={DARK}>
          {truncate(el.text || '', 20)}
        </text>
      </g>
    );
  }

  if (kind === 'icon') {
    return (
      <g>
        <circle cx={_x + _w / 2} cy={_y + _h / 2} r={Math.min(_w, _h) / 3} fill={LIGHT_BLUE} stroke={ACCENT} strokeWidth={0.5} />
        <text x={_x + _w / 2} y={_y + _h / 2 + 2} textAnchor="middle" fontSize={5} fill={ACCENT}>
          {el.name || 'icon'}
        </text>
      </g>
    );
  }

  // text_box (default)
  const role = el.role || 'body';
  const bg = role === 'label' ? '#EFF6FF' : role === 'kpi_number' ? '#F0F7FF' : 'white';
  const textColor = role === 'label' ? BLUE : role === 'kpi_number' ? ACCENT : DARK;
  const fw = role === 'label' || role === 'title' || el.bold ? 'bold' : 'normal';
  const fs = role === 'kpi_number' ? Math.min(12, _h * 0.4) : fontSize;

  return (
    <g>
      <rect x={_x} y={_y} width={_w} height={_h} fill={bg} stroke="#E9E9E7" strokeWidth={0.3} rx={1} />
      <text x={_x + 3} y={_y + Math.min(fs + 3, _h * 0.6)} fontSize={fs} fontWeight={fw} fill={textColor}>
        {truncate(el.text || '', 40)}
      </text>
    </g>
  );
}

export default function SlidePreview({ slide, selected, onClick, width = 280 }: Props) {
  const sType = slide.slide_type || slide.type || 'content';
  const title = slide.title || '';
  const height = width * 0.75; // 4:3

  const layoutElements = useMemo(() => {
    if (sType !== 'content' || !slide.elements?.length) return [];
    const hint = slide.layout_hint || 'auto';
    return computeLayout(slide.elements, hint);
  }, [slide, sType]);

  // Legacy support: left/right
  const isLegacy = !slide.elements && (slide.left || slide.right);

  return (
    <div
      className={`cursor-pointer rounded-lg border-2 transition-all overflow-hidden ${
        selected ? 'border-[#2383E2] shadow-md' : 'border-[#E9E9E7] hover:border-[#c0c0c0]'
      }`}
      style={{ width, height }}
      onClick={onClick}
    >
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} width="100%" height="100%">
        {/* Background */}
        {(sType === 'title' || sType === 'section') ? (
          <>
            <rect width={VB_W} height={VB_H} fill={BLUE} />
            <text x={VB_W / 2} y={VB_H * 0.45} textAnchor="middle" fontSize={14} fontWeight="bold" fill="white">
              {truncate(title, 30)}
            </text>
            {slide.subtitle && (
              <text x={VB_W / 2} y={VB_H * 0.58} textAnchor="middle" fontSize={8} fill={LIGHT_BLUE}>
                {truncate(slide.subtitle, 40)}
              </text>
            )}
          </>
        ) : (
          <>
            {/* White background */}
            <rect width={VB_W} height={VB_H} fill="white" />
            {/* Header bar */}
            <rect width={VB_W} height={HEADER_H} fill={BLUE} />
            <text x={8} y={14} fontSize={6} fill="white" fontWeight="bold">GEM Intern</text>
            {/* Title */}
            <text x={PAD} y={HEADER_H + 16} fontSize={10} fontWeight="bold" fill={BLUE}>
              {truncate(title, 45)}
            </text>

            {isLegacy ? (
              <>
                <rect x={CX} y={CY} width={CW / 2 - 2} height={CH} fill={GREY} stroke="#E9E9E7" strokeWidth={0.3} rx={2} />
                <text x={CX + 4} y={CY + 12} fontSize={6} fill={DARK}>Left column</text>
                <rect x={CX + CW / 2 + 2} y={CY} width={CW / 2 - 2} height={CH} fill={GREY} stroke="#E9E9E7" strokeWidth={0.3} rx={2} />
                <text x={CX + CW / 2 + 6} y={CY + 12} fontSize={6} fill={DARK}>Right column</text>
              </>
            ) : (
              layoutElements.map((el: any, i: number) => <ElementRect key={i} el={el} />)
            )}

            {/* Layout hint badge */}
            {slide.layout_hint && (
              <g>
                <rect x={VB_W - 70} y={VB_H - 14} width={66} height={12} fill={ACCENT} rx={3} opacity={0.8} />
                <text x={VB_W - 37} y={VB_H - 5} textAnchor="middle" fontSize={5} fill="white">
                  {slide.layout_hint}
                </text>
              </g>
            )}
          </>
        )}
      </svg>
    </div>
  );
}
