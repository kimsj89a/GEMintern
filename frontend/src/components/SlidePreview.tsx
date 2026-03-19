/**
 * SlidePreview — SVG-based schematic preview of a single slide.
 * Supports NP template types (data_table, chart_table, kpi_dashboard, etc.)
 * and legacy atomic elements (text_box, shape, chart, callout, icon).
 */
import { useMemo } from 'react';
import type { SlideData } from '../types/api';

// Layout constants (4:3 ratio scaled to viewBox 400x300)
const VB_W = 400;
const VB_H = 300;
const PAD = 10;
const HEADER_BAR_H = 4;
const HEADER_Y = HEADER_BAR_H + 2;
const TITLE_H = 18;
const CX = PAD;
const CY = HEADER_Y + TITLE_H + 12;
const CW = VB_W - PAD * 2;
const CH = VB_H - CY - 16;
const FOOTER_Y = VB_H - 12;

// NP Color palette (updated brand guide)
const NAVY = '#0C3064';
const BLUE = '#005DA2';
const YELLOW = '#CCA000';
const GOLD = YELLOW;
const DARK_GRAY = '#404040';
const RED = '#C00000';
const GREEN = '#008000';
const OFF_WHITE = '#F5F6F8';
const LIGHT_GRAY = '#D9DEE4';
const MID_GRAY = '#8892A5';
const DARK_TEXT = '#000000';
const WHITE = '#FFFFFF';
const PURPLE = '#5B2C8C';
const ORANGE = '#D97706';

const NP_TEMPLATE_TYPES = new Set([
  'title', 'divider', 'data_table', 'chart_table', 'two_column',
  'kpi_dashboard', 'risk_matrix', 'timeline_flow', 'comparison',
  'numbered_blocks', 'grid_cards',
]);

const SEVERITY_COLORS: Record<string, string> = {
  high: RED, critical: RED, medium: ORANGE, moderate: ORANGE, low: GREEN, info: BLUE,
};

const METRIC_COLORS: Record<string, string> = {
  blue: BLUE, green: GREEN, red: RED, purple: PURPLE, orange: ORANGE, gold: GOLD, navy: NAVY,
};

// SlideData imported from '../types/api'

interface Props {
  slide: SlideData;
  selected?: boolean;
  onClick?: () => void;
  width?: number;
}

function truncate(text: string, maxLen: number) {
  if (!text) return '';
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
}

/* ===== NP Header / Footer (schematic) ===== */
function NpHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <g>
      {/* Navy accent bar */}
      <rect x={0} y={0} width={VB_W} height={HEADER_BAR_H} fill={NAVY} />
      {/* Subtitle (section name) — above title */}
      {subtitle && (
        <text x={PAD} y={HEADER_Y + 8} fontSize={5} fill={BLUE}>
          {truncate(subtitle, 60)}
        </text>
      )}
      {/* Title — main heading */}
      <text x={PAD} y={HEADER_Y + (subtitle ? 22 : 14)} fontSize={10} fontWeight="bold" fill={DARK_TEXT}>
        {truncate(title, 45)}
      </text>
    </g>
  );
}

function NpFooter() {
  return (
    <g>
      <rect x={0} y={FOOTER_Y} width={VB_W} height={12} fill={NAVY} opacity={0.9} />
      <text x={PAD} y={FOOTER_Y + 8} fontSize={3.5} fill={MID_GRAY}>CONFIDENTIAL</text>
    </g>
  );
}

/* ===== Mini Table ===== */
function MiniTable({ headers, rows, x, y, w, h }: { headers: string[]; rows: any[][]; x: number; y: number; w: number; h: number }) {
  if (!headers?.length) return null;
  const cols = headers.length;
  const maxRows = Math.min(rows?.length || 0, Math.floor((h - 10) / 8));
  const colW = w / cols;
  const rowH = 8;

  return (
    <g>
      {/* Header row */}
      <rect x={x} y={y} width={w} height={rowH} fill={NAVY} rx={1} />
      {headers.map((h, i) => (
        <text key={i} x={x + i * colW + colW / 2} y={y + 5.5} textAnchor="middle" fontSize={3.5} fill={WHITE} fontWeight="bold">
          {truncate(String(h), Math.floor(colW / 3))}
        </text>
      ))}
      {/* Data rows */}
      {(rows || []).slice(0, maxRows).map((row, ri) => (
        <g key={ri}>
          <rect x={x} y={y + (ri + 1) * rowH} width={w} height={rowH} fill={ri % 2 === 0 ? '#F8F9FB' : WHITE} />
          {headers.map((_, ci) => (
            <text key={ci} x={x + ci * colW + colW / 2} y={y + (ri + 1) * rowH + 5.5} textAnchor="middle" fontSize={3} fill={DARK_TEXT}>
              {truncate(String(row[ci] ?? ''), Math.floor(colW / 3))}
            </text>
          ))}
        </g>
      ))}
    </g>
  );
}

/* ===== Mini KPI Cards ===== */
function MiniMetrics({ metrics, x, y, w }: { metrics: any[]; x: number; y: number; w: number }) {
  if (!metrics?.length) return null;
  const n = Math.min(metrics.length, 4);
  const gap = 3;
  const cardW = (w - gap * (n - 1)) / n;
  const cardH = 22;

  return (
    <g>
      {metrics.slice(0, n).map((m, i) => {
        const cx = x + i * (cardW + gap);
        const accent = METRIC_COLORS[m.color || 'blue'] || BLUE;
        return (
          <g key={i}>
            <rect x={cx} y={y} width={cardW} height={cardH} fill={WHITE} stroke={LIGHT_GRAY} strokeWidth={0.5} rx={2} />
            <rect x={cx} y={y} width={2} height={cardH} fill={accent} rx={1} />
            <text x={cx + 5} y={y + 9} fontSize={6} fontWeight="bold" fill={accent}>
              {truncate(String(m.value || ''), 10)}
            </text>
            <text x={cx + 5} y={y + 16} fontSize={3.5} fill={MID_GRAY}>
              {truncate(String(m.label || ''), 12)}
            </text>
            {m.sub && (
              <text x={cx + cardW - 3} y={y + 9} textAnchor="end" fontSize={3.5} fontWeight="bold"
                fill={String(m.sub).startsWith('+') ? GREEN : RED}>
                {truncate(String(m.sub), 8)}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}

/* ===== Mini Chart ===== */
function MiniChart({ chart, x, y, w, h }: { chart: any; x: number; y: number; w: number; h: number }) {
  const type = chart?.chart_type || 'bar';
  const series = chart?.series || [];
  const values = series[0]?.values || [];
  const maxVal = Math.max(...values.map(Number).filter((v: number) => !isNaN(v)), 1);

  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill={WHITE} stroke={LIGHT_GRAY} strokeWidth={0.5} rx={2} />
      <text x={x + w / 2} y={y + 7} textAnchor="middle" fontSize={3.5} fill={MID_GRAY}>{type}</text>
      {type === 'bar' || type === 'column' ? (
        values.slice(0, 6).map((v: number, i: number) => {
          const n = Math.min(values.length, 6);
          const barW = (w - 8) / n - 2;
          const barH = ((Number(v) || 0) / maxVal) * (h - 16);
          return (
            <rect key={i} x={x + 4 + i * (barW + 2)} y={y + h - 4 - barH}
              width={barW} height={barH} fill={NAVY} opacity={0.7} rx={1} />
          );
        })
      ) : type === 'line' ? (
        <polyline
          points={values.slice(0, 8).map((v: number, i: number) => {
            const n = Math.min(values.length, 8);
            const px = x + 6 + (i / Math.max(n - 1, 1)) * (w - 12);
            const py = y + h - 6 - ((Number(v) || 0) / maxVal) * (h - 18);
            return `${px},${py}`;
          }).join(' ')}
          fill="none" stroke={NAVY} strokeWidth={1.5}
        />
      ) : (
        <circle cx={x + w / 2} cy={y + h / 2 + 4} r={Math.min(w, h) / 3} fill={NAVY} opacity={0.3} stroke={GOLD} strokeWidth={1} />
      )}
    </g>
  );
}

/* ===== NP Template Renderers ===== */
function RenderTitle({ slide }: { slide: SlideData }) {
  return (
    <>
      <rect width={VB_W} height={VB_H} fill={NAVY} />
      {/* Gold accent line */}
      <rect x={PAD} y={VB_H * 0.42} width={60} height={2} fill={GOLD} />
      <text x={PAD} y={VB_H * 0.52} fontSize={14} fontWeight="bold" fill={WHITE} fontFamily="Georgia,serif">
        {truncate(slide.title || '', 35)}
      </text>
      {slide.subtitle && (
        <text x={PAD} y={VB_H * 0.62} fontSize={7} fill={LIGHT_GRAY}>
          {truncate(slide.subtitle, 50)}
        </text>
      )}
      <text x={PAD} y={VB_H * 0.85} fontSize={5} fill={MID_GRAY}>CONFIDENTIAL</text>
    </>
  );
}

function RenderDivider({ slide }: { slide: SlideData }) {
  return (
    <>
      <rect width={VB_W} height={VB_H} fill={NAVY} />
      {/* Gold circle with number */}
      <circle cx={VB_W / 2} cy={VB_H * 0.35} r={20} fill="none" stroke={GOLD} strokeWidth={1.5} />
      <text x={VB_W / 2} y={VB_H * 0.37} textAnchor="middle" fontSize={14} fontWeight="bold" fill={GOLD} fontFamily="Georgia,serif">
        {slide.section_number || ''}
      </text>
      <text x={VB_W / 2} y={VB_H * 0.58} textAnchor="middle" fontSize={11} fontWeight="bold" fill={WHITE} fontFamily="Georgia,serif">
        {truncate(slide.title || '', 30)}
      </text>
      {slide.subtitle && (
        <text x={VB_W / 2} y={VB_H * 0.68} textAnchor="middle" fontSize={6} fill={MID_GRAY}>
          {truncate(slide.subtitle, 40)}
        </text>
      )}
    </>
  );
}

function RenderDataTable({ slide }: { slide: SlideData }) {
  const table = slide.table;
  const metrics = slide.metrics || slide.kpi_cards || [];
  const tableH = metrics.length > 0 ? CH - 28 : CH;

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {table?.headers && (
        <MiniTable headers={table.headers} rows={table.rows || []} x={CX} y={CY} w={CW} h={tableH} />
      )}
      {metrics.length > 0 && (
        <MiniMetrics metrics={metrics} x={CX} y={CY + tableH + 3} w={CW} />
      )}
      <NpFooter />
    </>
  );
}

function RenderChartTable({ slide }: { slide: SlideData }) {
  const chart = slide.chart;
  const table = slide.table;
  const leftW = CW * 0.58;
  const rightW = CW - leftW - 4;

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      <MiniChart chart={chart} x={CX} y={CY} w={leftW} h={CH} />
      {table?.headers && (
        <MiniTable headers={table.headers} rows={table.rows || []} x={CX + leftW + 4} y={CY} w={rightW} h={CH} />
      )}
      {slide.banner && (
        <g>
          <rect x={CX} y={CY + CH - 12} width={CW} height={10} fill={NAVY} rx={1} />
          <text x={CX + 4} y={CY + CH - 5} fontSize={3.5} fill={GOLD} fontWeight="bold">
            {truncate(String(slide.banner.label || ''), 8)}
          </text>
          <text x={CX + 30} y={CY + CH - 5} fontSize={3.5} fill={WHITE}>
            {truncate(String(slide.banner.text || ''), 40)}
          </text>
        </g>
      )}
      <NpFooter />
    </>
  );
}

function RenderTwoColumn({ slide }: { slide: SlideData }) {
  const left = slide.left || slide.left_column || {};
  const right = slide.right || slide.right_column || {};
  const halfW = CW / 2 - 2;

  const renderCol = (col: any, x: number, w: number) => {
    if (!col) return null;
    const colTitle = typeof col === 'object' ? (col.title || col.name || '') : '';
    const items = typeof col === 'object' ? (col.items || []) : (Array.isArray(col) ? col : []);
    const colTable = typeof col === 'object' ? col.table : null;

    return (
      <g>
        {colTitle && (
          <>
            <rect x={x} y={CY} width={w} height={10} fill={NAVY} rx={1} />
            <text x={x + 3} y={CY + 7} fontSize={4} fontWeight="bold" fill={WHITE}>{truncate(colTitle, 20)}</text>
          </>
        )}
        {colTable?.headers ? (
          <MiniTable headers={colTable.headers} rows={colTable.rows || []} x={x} y={CY + (colTitle ? 13 : 0)} w={w} h={CH - (colTitle ? 13 : 0)} />
        ) : (
          items.slice(0, 6).map((item: any, i: number) => (
            <text key={i} x={x + 3} y={CY + (colTitle ? 18 : 6) + i * 8} fontSize={3.5} fill={DARK_TEXT}>
              {'\u2022 ' + truncate(String(item), 25)}
            </text>
          ))
        )}
      </g>
    );
  };

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {renderCol(left, CX, halfW)}
      {renderCol(right, CX + halfW + 4, halfW)}
      <NpFooter />
    </>
  );
}

function RenderKpiDashboard({ slide }: { slide: SlideData }) {
  const metrics = slide.metrics || slide.kpi_cards || [];
  const table = slide.table;
  const chart = slide.chart;
  const hasTable = table?.headers?.length;
  const hasChart = chart?.categories?.length;
  const mainH = CH - (metrics.length > 0 ? 28 : 0);

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {hasTable ? (
        <MiniTable headers={table!.headers} rows={table!.rows || []} x={CX} y={CY} w={CW} h={mainH} />
      ) : hasChart ? (
        <MiniChart chart={chart} x={CX} y={CY} w={CW} h={mainH} />
      ) : slide.content ? (
        <text x={CX + 3} y={CY + 10} fontSize={4} fill={DARK_TEXT}>{truncate(slide.content, 80)}</text>
      ) : null}
      {metrics.length > 0 && (
        <MiniMetrics metrics={metrics} x={CX} y={CY + mainH + 3} w={CW} />
      )}
      <NpFooter />
    </>
  );
}

function RenderRiskMatrix({ slide }: { slide: SlideData }) {
  const risks = slide.risks || slide.items || [];
  const n = Math.min(risks.length, 6);
  const cols = Math.min(n, 3);
  const rows = Math.ceil(n / cols);
  const gap = 3;
  const cardW = (CW - gap * (cols - 1)) / cols;
  const cardH = (CH - gap * (rows - 1)) / rows;

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {risks.slice(0, n).map((risk: any, i: number) => {
        const r = Math.floor(i / cols);
        const c = i % cols;
        const rx = CX + c * (cardW + gap);
        const ry = CY + r * (cardH + gap);
        const severity = String(risk.severity || risk.level || 'medium').toLowerCase();
        const sevColor = SEVERITY_COLORS[severity] || ORANGE;

        return (
          <g key={i}>
            <rect x={rx} y={ry} width={cardW} height={cardH} fill={WHITE} stroke={LIGHT_GRAY} strokeWidth={0.5} rx={2} />
            <rect x={rx} y={ry} width={cardW} height={2} fill={sevColor} />
            {/* Severity badge */}
            <rect x={rx + cardW - 22} y={ry + 3} width={20} height={7} fill={sevColor} rx={2} />
            <text x={rx + cardW - 12} y={ry + 8} textAnchor="middle" fontSize={3} fill={WHITE} fontWeight="bold">
              {severity.toUpperCase()}
            </text>
            <text x={rx + 3} y={ry + 9} fontSize={3.5} fontWeight="bold" fill={NAVY}>
              {truncate(risk.category || risk.title || '', 18)}
            </text>
            <text x={rx + 3} y={ry + 17} fontSize={3} fill={MID_GRAY}>
              {truncate(risk.description || risk.text || '', 28)}
            </text>
          </g>
        );
      })}
      <NpFooter />
    </>
  );
}

function RenderTimelineFlow({ slide }: { slide: SlideData }) {
  const nodes = slide.nodes || slide.items || slide.steps || [];
  const n = Math.min(nodes.length, 8);
  const nodeR = 12;
  const spacing = n > 1 ? (CW - nodeR * 2) / (n - 1) : 0;
  const midY = CY + CH * 0.3;
  const ACCENT_COLORS = [BLUE, GREEN, PURPLE, ORANGE, RED, GOLD];

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {/* Connector line */}
      {n > 1 && (
        <rect x={CX + nodeR} y={midY - 1} width={CW - nodeR * 2} height={2} fill={LIGHT_GRAY} rx={1} />
      )}
      {nodes.slice(0, n).map((node: any, i: number) => {
        const nx = CX + nodeR + i * spacing;
        const accent = ACCENT_COLORS[i % ACCENT_COLORS.length];
        const nodeTitle = typeof node === 'object' ? (node.title || node) : String(node);
        const nodeLabel = typeof node === 'object' ? (node.label || String(i + 1)) : String(i + 1);
        const nodeDesc = typeof node === 'object' ? (node.description || '') : '';

        return (
          <g key={i}>
            <circle cx={nx} cy={midY} r={nodeR} fill={accent} />
            <text x={nx} y={midY + 2} textAnchor="middle" fontSize={5} fontWeight="bold" fill={WHITE}>
              {truncate(String(nodeLabel), 3)}
            </text>
            <text x={nx} y={midY + nodeR + 10} textAnchor="middle" fontSize={4} fontWeight="bold" fill={NAVY}>
              {truncate(String(nodeTitle), 10)}
            </text>
            {nodeDesc && (
              <text x={nx} y={midY + nodeR + 18} textAnchor="middle" fontSize={3} fill={MID_GRAY}>
                {truncate(String(nodeDesc), 12)}
              </text>
            )}
          </g>
        );
      })}
      <NpFooter />
    </>
  );
}

function RenderComparison({ slide }: { slide: SlideData }) {
  const left = slide.left || {};
  const right = slide.right || {};
  const halfW = CW / 2 - 8;
  const verdict = slide.verdict || slide.conclusion || '';

  const renderSide = (side: any, x: number, accent: string) => {
    const sideTitle = side.title || side.name || '';
    const items = side.items || [];

    return (
      <g>
        <rect x={x} y={CY + 8} width={halfW} height={12} fill={accent} rx={1} />
        <text x={x + 3} y={CY + 16} fontSize={4} fontWeight="bold" fill={WHITE}>{truncate(sideTitle, 18)}</text>
        {items.slice(0, 5).map((item: any, i: number) => (
          <text key={i} x={x + 3} y={CY + 28 + i * 8} fontSize={3.5} fill={DARK_TEXT}>
            {'\u2022 ' + truncate(String(item), 22)}
          </text>
        ))}
      </g>
    );
  };

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {/* VS badge */}
      <ellipse cx={VB_W / 2} cy={CY + 13} rx={12} ry={6} fill={GOLD} />
      <text x={VB_W / 2} y={CY + 15} textAnchor="middle" fontSize={5} fontWeight="bold" fill={WHITE}>VS</text>
      {renderSide(left, CX, BLUE)}
      {renderSide(right, CX + halfW + 16, NAVY)}
      {verdict && (
        <g>
          <rect x={CX} y={CY + CH - 12} width={CW} height={10} fill={NAVY} rx={1} />
          <text x={CX + 4} y={CY + CH - 5} fontSize={3.5} fill={GOLD} fontWeight="bold">결론:</text>
          <text x={CX + 22} y={CY + CH - 5} fontSize={3.5} fill={WHITE}>{truncate(verdict, 50)}</text>
        </g>
      )}
      <NpFooter />
    </>
  );
}

function RenderNumberedBlocks({ slide }: { slide: SlideData }) {
  const blocks = slide.blocks || slide.items || [];
  const n = Math.min(blocks.length, 6);
  const cols = n > 1 ? 2 : 1;
  const rows = Math.ceil(n / cols);
  const gap = 4;
  const blockW = (CW - gap * (cols - 1)) / cols;
  const blockH = Math.min((CH - gap * (rows - 1)) / rows, 50);

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {blocks.slice(0, n).map((b: any, i: number) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const bx = CX + col * (blockW + gap);
        const by = CY + row * (blockH + gap);
        return (
          <g key={i}>
            <rect x={bx} y={by} width={18} height={14} fill={NAVY} rx={2} />
            <text x={bx + 9} y={by + 10} textAnchor="middle" fontSize={6} fontWeight="bold" fill={WHITE}>
              {b.number || `${i + 1}`.padStart(2, '0')}
            </text>
            <text x={bx + 22} y={by + 10} fontSize={4.5} fontWeight="bold" fill={NAVY}>
              {truncate(b.title || '', 22)}
            </text>
            <text x={bx + 22} y={by + 20} fontSize={3} fill={DARK_GRAY}>
              {truncate(b.description || '', 35)}
            </text>
            <rect x={bx} y={by + blockH - 1} width={blockW} height={0.5} fill={LIGHT_GRAY} />
          </g>
        );
      })}
      <NpFooter />
    </>
  );
}

function RenderGridCards({ slide }: { slide: SlideData }) {
  const cards = slide.cards || [];
  const n = Math.min(cards.length, 4);
  const gap = 4;
  const cardW = (CW - gap * (n - 1)) / n;
  const cardH = CH - 4;

  return (
    <>
      <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
      <NpHeader title={slide.title || ''} subtitle={slide.subtitle} />
      {cards.slice(0, n).map((c: any, i: number) => {
        const cx = CX + i * (cardW + gap);
        const items = c.items || [];
        return (
          <g key={i}>
            <rect x={cx} y={CY} width={cardW} height={cardH} fill={WHITE} stroke={LIGHT_GRAY} strokeWidth={0.5} rx={2} />
            <rect x={cx} y={CY} width={cardW} height={12} fill={NAVY} rx={2} />
            <rect x={cx} y={CY + 10} width={cardW} height={4} fill={NAVY} />
            <text x={cx + cardW / 2} y={CY + 8} textAnchor="middle" fontSize={4} fontWeight="bold" fill={WHITE}>
              {truncate(c.title || '', 12)}
            </text>
            {c.subtitle && (
              <text x={cx + 3} y={CY + 20} fontSize={3} fill={MID_GRAY}>{truncate(c.subtitle, 15)}</text>
            )}
            {items.slice(0, 5).map((item: string, j: number) => (
              <text key={j} x={cx + 3} y={CY + (c.subtitle ? 28 : 20) + j * 7} fontSize={3} fill={DARK_TEXT}>
                {'\u2022 ' + truncate(String(item), 18)}
              </text>
            ))}
          </g>
        );
      })}
      <NpFooter />
    </>
  );
}

/* ===== Legacy Element Renderers ===== */
function computeLayout(elements: any[], hint: string) {
  if (!elements?.length) return [];
  const n = elements.length;
  const positioned = elements.map((el: any, i: number) => ({ ...el, _idx: i }));

  switch (hint) {
    case 'single_column': {
      const h = CH / n;
      return positioned.map((el: any, i: number) => ({ ...el, _x: CX, _y: CY + i * h, _w: CW, _h: h - 2 }));
    }
    case 'two_column': {
      const half = Math.ceil(n / 2);
      return positioned.map((el: any, i: number) => {
        const col = i < half ? 0 : 1;
        const row = col === 0 ? i : i - half;
        const rows = col === 0 ? half : n - half;
        const h = CH / Math.max(rows, 1);
        return { ...el, _x: CX + col * (CW / 2 + 2), _y: CY + row * h, _w: CW / 2 - 2, _h: h - 2 };
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
    case 'process_flow':
    case 'timeline': {
      const w = CW / n - 4;
      return positioned.map((el: any, i: number) => ({
        ...el, _x: CX + i * (w + 4), _y: CY + CH * 0.2, _w: w, _h: CH * 0.6,
      }));
    }
    default: {
      const h = CH / n;
      return positioned.map((el: any, i: number) => ({ ...el, _x: CX, _y: CY + i * h, _w: CW, _h: h - 2 }));
    }
  }
}

function ElementRect({ el }: { el: any }) {
  const { _x, _y, _w, _h, kind } = el;
  if (_w < 2 || _h < 2) return null;
  const fontSize = Math.min(5, _h * 0.25);

  if (kind === 'chart') {
    return (
      <g>
        <rect x={_x} y={_y} width={_w} height={_h} fill={OFF_WHITE} stroke={NAVY} strokeWidth={0.5} rx={2} />
        {[0.2, 0.4, 0.6, 0.8].map((pct, i) => {
          const bh = _h * (0.3 + Math.random() * 0.4);
          return <rect key={i} x={_x + _w * pct - _w * 0.06} y={_y + _h - bh - 4} width={_w * 0.12} height={bh} fill={NAVY} opacity={0.6 + i * 0.1} rx={1} />;
        })}
      </g>
    );
  }

  if (kind === 'callout') {
    return (
      <g>
        <rect x={_x} y={_y} width={_w} height={_h} fill={WHITE} stroke={GOLD} strokeWidth={0.8} rx={2} />
        <rect x={_x} y={_y} width={2} height={_h} fill={GOLD} />
        <text x={_x + _w / 2} y={_y + _h * 0.4} textAnchor="middle" fontSize={Math.min(8, _h * 0.3)} fontWeight="bold" fill={GOLD}>
          {truncate(el.value || '', 10)}
        </text>
        <text x={_x + _w / 2} y={_y + _h * 0.65} textAnchor="middle" fontSize={fontSize} fill={DARK_TEXT}>
          {truncate(el.label || '', 15)}
        </text>
      </g>
    );
  }

  if (kind === 'shape') {
    const fill = el.fill || OFF_WHITE;
    return (
      <g>
        <rect x={_x} y={_y} width={_w} height={_h} fill={fill} stroke={NAVY} strokeWidth={0.5} rx={el.shape_type?.includes('round') ? 4 : 1} />
        <text x={_x + _w / 2} y={_y + _h / 2 + 2} textAnchor="middle" fontSize={fontSize} fill={DARK_TEXT}>
          {truncate(el.text || '', 20)}
        </text>
      </g>
    );
  }

  // text_box (default)
  const role = el.role || 'body';
  const bg = role === 'label' ? '#EFF6FF' : WHITE;
  const textColor = role === 'label' ? NAVY : DARK_TEXT;
  const fw = role === 'label' || role === 'title' || el.bold ? 'bold' : 'normal';

  return (
    <g>
      <rect x={_x} y={_y} width={_w} height={_h} fill={bg} stroke={LIGHT_GRAY} strokeWidth={0.3} rx={1} />
      <text x={_x + 3} y={_y + Math.min(fontSize + 3, _h * 0.6)} fontSize={fontSize} fontWeight={fw} fill={textColor}>
        {truncate(el.text || '', 40)}
      </text>
    </g>
  );
}

/* ===== Dynamic Element Renderer (좌표 기반 elements[]) ===== */
// 인치 → SVG viewBox 좌표 변환 (10" = 400px, 5.63" ≈ 300px)
const INCH_X = 40;  // 1 inch = 40px in viewBox
const INCH_Y = 53.3; // 1 inch ≈ 53.3px in viewBox (300/5.63)

function DynamicElement({ el }: { el: any }) {
  const x = (el.x ?? 0) * INCH_X;
  const y = (el.y ?? 0) * INCH_Y;
  const w = (el.w ?? 1) * INCH_X;
  const h = (el.h ?? 0.5) * INCH_Y;

  switch (el.type) {
    case 'text': {
      const fs = Math.min((el.fontSize ?? 11) * 0.4, 12);
      const color = el.color ? `#${el.color}` : '#2D2D2D';
      const textStr = Array.isArray(el.text)
        ? el.text.map((r: any) => typeof r === 'string' ? r : r.text || '').join('')
        : (el.text || '');
      const fill = el.fill ? `#${el.fill}` : undefined;
      return (
        <g>
          {fill && <rect x={x} y={y} width={w} height={h} fill={fill} rx={2} stroke={el.borderColor ? `#${el.borderColor}` : undefined} strokeWidth={el.borderColor ? 0.5 : 0} />}
          <text x={x + 2} y={y + fs + 2} fontSize={fs} fontWeight={el.bold ? 'bold' : 'normal'} fill={color} opacity={0.9}>
            {truncate(textStr, Math.floor(w / (fs * 0.5)))}
          </text>
        </g>
      );
    }
    case 'shape': {
      const fill = el.fill ? `#${el.fill}` : '#F6F6F6';
      return <rect x={x} y={y} width={w} height={h} fill={fill} rx={el.rectRadius ? el.rectRadius * 4 : 1} />;
    }
    case 'table': {
      const rows = el.rows || [];
      if (rows.length === 0) return null;
      const cols = rows[0]?.length || 1;
      const colW = w / cols;
      const rowH = Math.min(h / rows.length, 10);
      return (
        <g>
          {rows.slice(0, 8).map((row: any[], ri: number) => (
            <g key={ri}>
              <rect x={x} y={y + ri * rowH} width={w} height={rowH}
                fill={ri === 0 ? '#1B2A4A' : ri % 2 === 0 ? '#F2F5F7' : WHITE} />
              {row.slice(0, 6).map((cell: any, ci: number) => {
                const cellText = typeof cell === 'object' ? (cell.text || '') : String(cell ?? '');
                return (
                  <text key={ci} x={x + ci * colW + colW / 2} y={y + ri * rowH + rowH * 0.65}
                    textAnchor="middle" fontSize={3.5} fill={ri === 0 ? WHITE : '#2D2D2D'}
                    fontWeight={ri === 0 ? 'bold' : 'normal'}>
                    {truncate(cellText, Math.floor(colW / 3))}
                  </text>
                );
              })}
            </g>
          ))}
        </g>
      );
    }
    case 'chart': {
      const data = el.data || [];
      const values = data[0]?.values || [];
      const maxVal = Math.max(...values.map(Number).filter((v: number) => !isNaN(v)), 1);
      return (
        <g>
          <rect x={x} y={y} width={w} height={h} fill={WHITE} stroke="#E0E0E0" strokeWidth={0.5} rx={2} />
          {values.slice(0, 8).map((v: number, i: number) => {
            const n = Math.min(values.length, 8);
            const barW = (w - 8) / n - 2;
            const barH = ((Number(v) || 0) / maxVal) * (h - 12);
            return <rect key={i} x={x + 4 + i * (barW + 2)} y={y + h - 4 - barH} width={barW} height={barH} fill="#1B2A4A" opacity={0.7} rx={1} />;
          })}
        </g>
      );
    }
    case 'kpi_card': {
      return (
        <g>
          <rect x={x} y={y} width={w} height={h} fill={WHITE} stroke="#E0E0E0" strokeWidth={0.5} rx={3} />
          <rect x={x} y={y + 1} width={2} height={h - 2} fill="#86BC25" rx={1} />
          <text x={x + 5} y={y + h * 0.35} fontSize={4} fill="#6B6B6B">{truncate(el.label || '', 12)}</text>
          <text x={x + 5} y={y + h * 0.65} fontSize={7} fontWeight="bold" fill="#1B2A4A">{truncate(el.value || '', 10)}</text>
          {el.change && <text x={x + w - 3} y={y + h * 0.35} textAnchor="end" fontSize={3.5} fontWeight="bold"
            fill={String(el.change).includes('+') ? '#86BC25' : '#C4262E'}>{truncate(el.change, 8)}</text>}
        </g>
      );
    }
    case 'callout': {
      return (
        <g>
          <rect x={x} y={y} width={w} height={h} fill="#F6F6F6" stroke="#E0E0E0" strokeWidth={0.5} rx={2} />
          <rect x={x} y={y + 1} width={2} height={h - 2} fill={el.accentColor ? `#${el.accentColor}` : '#86BC25'} />
          <text x={x + 5} y={y + h * 0.35} fontSize={3.5} fill="#6B6B6B">{truncate(el.label || '', 15)}</text>
          <text x={x + 5} y={y + h * 0.65} fontSize={7} fontWeight="bold" fill="#1B2A4A">{truncate(el.value || '', 12)}</text>
        </g>
      );
    }
    case 'divider':
      return <rect x={x} y={y} width={w} height={1} fill="#E0E0E0" />;
    default:
      return null;
  }
}

/* ===== Main Component ===== */
export default function SlidePreview({ slide, selected, onClick, width = 280 }: Props) {
  const sType = slide.slide_type || slide.type || 'content';
  const height = width * (9 / 16); // 16:9 ratio for dynamic, 4:3 for NP
  const isNpTemplate = NP_TEMPLATE_TYPES.has(sType);
  const isDynamic = !!(slide as any).elements?.length;

  const layoutElements = useMemo(() => {
    if (isNpTemplate || isDynamic || !slide.elements?.length) return [];
    const hint = slide.layout_hint || 'auto';
    return computeLayout(slide.elements, hint);
  }, [slide, isNpTemplate, isDynamic]);

  return (
    <div
      className={`cursor-pointer rounded-lg border-2 transition-all overflow-hidden ${
        selected ? 'border-blue-500 shadow-md' : 'border-[#E9E9E7] hover:border-[#c0c0c0]'
      }`}
      style={{ width, height }}
      onClick={onClick}
    >
      <svg viewBox={`0 0 ${VB_W} ${isDynamic ? 225 : VB_H}`} width="100%" height="100%">
        {isDynamic ? (
          /* ===== 좌표 기반 동적 렌더링 ===== */
          <>
            <rect width={VB_W} height={225} fill={`#${(slide as any).background || 'FFFFFF'}`} />
            {((slide as any).elements || []).map((el: any, i: number) => (
              <DynamicElement key={i} el={el} />
            ))}
          </>
        ) : isNpTemplate ? (
          <>
            {sType === 'title' && <RenderTitle slide={slide} />}
            {sType === 'divider' && <RenderDivider slide={slide} />}
            {sType === 'data_table' && <RenderDataTable slide={slide} />}
            {sType === 'chart_table' && <RenderChartTable slide={slide} />}
            {sType === 'two_column' && <RenderTwoColumn slide={slide} />}
            {sType === 'kpi_dashboard' && <RenderKpiDashboard slide={slide} />}
            {sType === 'risk_matrix' && <RenderRiskMatrix slide={slide} />}
            {sType === 'timeline_flow' && <RenderTimelineFlow slide={slide} />}
            {sType === 'comparison' && <RenderComparison slide={slide} />}
            {sType === 'numbered_blocks' && <RenderNumberedBlocks slide={slide} />}
            {sType === 'grid_cards' && <RenderGridCards slide={slide} />}
          </>
        ) : (
          <>
            <rect width={VB_W} height={VB_H} fill={OFF_WHITE} />
            <NpHeader title={slide.title || ''} />
            {layoutElements.map((el: any, i: number) => <ElementRect key={i} el={el} />)}
            <NpFooter />
          </>
        )}
      </svg>
    </div>
  );
}
