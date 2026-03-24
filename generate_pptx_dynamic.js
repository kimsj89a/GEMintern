/**
 * generate_pptx_dynamic.js — 좌표 기반 동적 PPT 렌더러
 *
 * AI가 각 슬라이드의 요소 배치(x, y, w, h)를 직접 결정.
 * 고정 마스터 없이, 콘텐츠에 따라 자유 레이아웃 구성.
 *
 * 요소 타입: text, table, chart, shape, kpi_card, callout, divider, icon_text
 */

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

// pptxgenjs v4: shapes/charts는 인스턴스 프로퍼티
const _pres = new pptxgen();
const SHAPES = _pres.shapes;
const CHARTS = _pres.charts;

// ── 기본 팔레트 (Noh & Partners IM Brand) ──
const PALETTE = {
  primary: "0C3064",       // Navy (main)
  accent: "CCA000",        // Gold (subsection stripe, highlight)
  secondary: "005DA2",     // Blue
  alert: "C00000",         // Red (key figures, warning)
  bg_dark: "0C3064",       // Navy background
  bg_light: "F2F2F2",      // Light grey (table alt rows)
  text_dark: "404040",     // Dark grey (body text, NOT #000)
  text_secondary: "64748B", // Muted slate (footnotes, source)
  text_light: "FFFFFF",
  chart_colors: ["0C3064", "005DA2", "00A2E8", "CCA000", "C00000", "404040"],
  gray: "64748B",
  border: "BFBFBF",
  table_alt: "F2F2F2",
  card_bg: "FFFFFF",
};

// ── 요소 렌더러 ──

function renderText(slide, el) {
  const opts = {
    x: el.x ?? 0.5,
    y: el.y ?? 0.5,
    w: el.w ?? 9,
    h: el.h ?? 0.5,
    fontSize: el.fontSize ?? 12,
    fontFace: el.fontFace ?? "Arial",
    color: el.color ?? PALETTE.text_dark,
    bold: el.bold ?? false,
    italic: el.italic ?? false,
    align: el.align ?? "left",
    valign: el.valign ?? "top",
    lineSpacingMultiple: el.lineSpacing ?? 1.2,
    wrap: true,
  };

  if (el.fill) opts.fill = { color: el.fill };
  if (el.borderColor) {
    opts.border = { pt: el.borderPt ?? 1, color: el.borderColor };
  }
  if (el.rectRadius) opts.rectRadius = el.rectRadius;
  if (el.charSpacing) opts.charSpacing = el.charSpacing;
  if (el.bullet) opts.bullet = el.bullet;
  if (el.paraSpaceAfter) opts.paraSpaceAfter = el.paraSpaceAfter;

  // 리치 텍스트 지원: el.text가 배열이면 runs로 처리
  if (Array.isArray(el.text)) {
    const runs = el.text.map(run => {
      if (typeof run === "string") return { text: run };
      return {
        text: run.text || "",
        options: {
          fontSize: run.fontSize ?? opts.fontSize,
          fontFace: run.fontFace ?? opts.fontFace,
          color: run.color ?? opts.color,
          bold: run.bold ?? opts.bold,
          italic: run.italic ?? false,
          breakLine: run.breakLine ?? false,
        },
      };
    });
    slide.addText(runs, opts);
  } else {
    slide.addText(el.text || "", opts);
  }
}

function renderTable(slide, el) {
  const rows = el.rows || [];
  if (rows.length === 0) return;

  // 헤더 스타일
  const headerOpts = {
    fill: { color: el.headerFill ?? PALETTE.primary },
    color: el.headerColor ?? PALETTE.text_light,
    bold: true,
    fontSize: el.fontSize ?? 10,
    fontFace: "Calibri",
    align: "center",
    valign: "middle",
  };

  // 본문 스타일
  const bodyOpts = {
    fontSize: el.fontSize ?? 10,
    fontFace: "Calibri Light",
    color: el.bodyColor ?? PALETTE.text_dark,
    valign: "middle",
  };

  const totalRow = el.totalRow ?? false;
  const lastRowIdx = rows.length - 1;

  const tableRows = rows.map((row, ri) => {
    return row.map(cell => {
      const cellText = cell?.text ?? cell?.toString?.() ?? String(cell ?? "");
      const isHeader = ri === 0;
      const isTotalRow = totalRow && ri === lastRowIdx;
      const cellOpts = isHeader ? { ...headerOpts } : { ...bodyOpts };

      // totalRow: bold + top border
      if (isTotalRow) {
        cellOpts.bold = true;
        cellOpts.border = [{ pt: 1.5, color: PALETTE.primary }, null, null, null];
      }

      // 셀별 커스텀
      if (cell && typeof cell === "object") {
        if (cell.fill) cellOpts.fill = { color: cell.fill };
        if (cell.color) cellOpts.color = cell.color;
        if (cell.bold !== undefined) cellOpts.bold = cell.bold;
        if (cell.align) cellOpts.align = cell.align;
      }

      // 짝수행 배경 (totalRow 제외)
      if (!isHeader && !isTotalRow && ri % 2 === 0) {
        cellOpts.fill = cellOpts.fill || { color: PALETTE.table_alt };
      }

      return { text: cellText, options: cellOpts };
    });
  });

  const colW = el.colWidths ?? undefined;

  slide.addTable(tableRows, {
    x: el.x ?? 0.5,
    y: el.y ?? 1.5,
    w: el.w ?? 9,
    colW: colW,
    border: { pt: 0.5, color: PALETTE.border },
    rowH: el.rowH ?? undefined,
    autoPage: false,
  });
}

function renderChart(slide, el) {
  const chartType = el.chartType || "bar";
  const data = el.data || [];

  // pptxgenjs 차트 타입 매핑
  const typeMap = {
    bar: CHARTS.BAR,
    line: CHARTS.LINE,
    pie: CHARTS.PIE,
    doughnut: CHARTS.DOUGHNUT,
    area: CHARTS.AREA,
  };

  const pptxType = typeMap[chartType] ?? CHARTS.BAR;

  // data 형식: [{name: "시리즈명", labels: [...], values: [...]}]
  const chartData = data.map(d => ({
    name: d.name || "",
    labels: d.labels || [],
    values: (d.values || []).map(v => typeof v === "number" ? v : parseFloat(v) || 0),
  }));

  if (chartData.length === 0) return;

  const opts = {
    x: el.x ?? 0.5,
    y: el.y ?? 1.5,
    w: el.w ?? 6,
    h: el.h ?? 3.5,
    chartColors: el.colors ?? PALETTE.chart_colors,
    showTitle: !!el.title,
    title: el.title || "",
    titleFontSize: 10,
    titleColor: PALETTE.text_dark,
    showValue: el.showValue ?? false,
    showLegend: el.showLegend ?? true,
    legendPos: el.legendPos ?? "b",
    legendFontSize: 8,
    catAxisLabelFontSize: 8,
    valAxisLabelFontSize: 8,
    catAxisOrientation: el.catAxisOrientation ?? "minMax",
    valAxisHidden: el.valAxisHidden ?? false,
    catAxisHidden: el.catAxisHidden ?? false,
  };

  // Column chart (vertical bars)
  if (chartType === "bar") {
    opts.barDir = el.barDir ?? "bar";
  }

  // Axis titles
  if (el.showCatAxisTitle && el.catAxisTitle) {
    opts.showCatAxisTitle = true;
    opts.catAxisTitle = el.catAxisTitle;
    opts.catAxisTitleFontSize = el.catAxisTitleFontSize ?? 9;
    opts.catAxisTitleColor = PALETTE.text_secondary;
  }
  if (el.showValAxisTitle && el.valAxisTitle) {
    opts.showValAxisTitle = true;
    opts.valAxisTitle = el.valAxisTitle;
    opts.valAxisTitleFontSize = el.valAxisTitleFontSize ?? 9;
    opts.valAxisTitleColor = PALETTE.text_secondary;
  }

  slide.addChart(pptxType, chartData, opts);
}

function renderShape(slide, el) {
  const shapeType = el.shapeType || "rect";
  const shapeMap = {
    rect: SHAPES.RECTANGLE,
    roundRect: SHAPES.ROUNDED_RECTANGLE,
    ellipse: SHAPES.OVAL,
    line: SHAPES.LINE,
  };

  slide.addShape(shapeMap[shapeType] ?? SHAPES.RECTANGLE, {
    x: el.x ?? 0,
    y: el.y ?? 0,
    w: el.w ?? 1,
    h: el.h ?? 1,
    fill: { color: el.fill ?? PALETTE.bg_light },
    line: el.borderColor ? { color: el.borderColor, width: el.borderPt ?? 1 } : undefined,
    rectRadius: el.rectRadius ?? 0.05,
  });
}

function renderKpiCard(slide, el) {
  const x = el.x ?? 0.5;
  const y = el.y ?? 1.5;
  const w = el.w ?? 2;
  const h = el.h ?? 1.2;

  // 카드 배경
  slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: el.fill ?? PALETTE.card_bg },
    line: { color: PALETTE.border, width: 0.5 },
    rectRadius: 0.1,
    shadow: { type: "outer", blur: 3, offset: 1, color: "000000", opacity: 0.1 },
  });

  // 레이블
  slide.addText(el.label || "", {
    x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.3,
    fontSize: 9, fontFace: "Calibri", color: PALETTE.gray,
  });

  // 값
  slide.addText(el.value || "", {
    x: x + 0.15, y: y + 0.35, w: w - 0.3, h: 0.4,
    fontSize: 20, fontFace: "Calibri", color: PALETTE.primary, bold: true,
  });

  // 변화율/설명
  if (el.change || el.description) {
    const changeText = el.change || el.description || "";
    const isPositive = changeText.includes("+") || changeText.includes("▲");
    slide.addText(changeText, {
      x: x + 0.15, y: y + 0.75, w: w - 0.3, h: 0.3,
      fontSize: 9, fontFace: "Calibri",
      color: isPositive ? "22C55E" : el.change ? "EF4444" : PALETTE.gray,
    });
  }
}

function renderCallout(slide, el) {
  const x = el.x ?? 0.5;
  const y = el.y ?? 1.5;
  const w = el.w ?? 3;
  const h = el.h ?? 1.0;
  const accentColor = el.accentColor ?? PALETTE.accent;

  // Background rounded rect
  slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: el.fill ?? PALETTE.bg_light },
    line: { color: PALETTE.border, width: 0.5 },
    rectRadius: 0.08,
  });

  // Left accent bar (4px colored strip)
  slide.addShape(SHAPES.RECTANGLE, {
    x: x, y: y + 0.05, w: 0.06, h: h - 0.1,
    fill: { color: accentColor },
  });

  // Label text (8pt gray)
  if (el.label) {
    slide.addText(el.label, {
      x: x + 0.2, y: y + 0.08, w: w - 0.35, h: 0.22,
      fontSize: 8, fontFace: "Calibri", color: PALETTE.text_secondary,
    });
  }

  // Value text (20pt bold navy)
  slide.addText(el.value || "", {
    x: x + 0.2, y: y + (el.label ? 0.28 : 0.1), w: w - 0.35, h: 0.4,
    fontSize: el.valueFontSize ?? 20, fontFace: "Calibri",
    color: el.valueColor ?? PALETTE.primary, bold: true,
  });

  // Optional subtitle (9pt)
  if (el.subtitle) {
    slide.addText(el.subtitle, {
      x: x + 0.2, y: y + h - 0.3, w: w - 0.35, h: 0.22,
      fontSize: 9, fontFace: "Calibri", color: PALETTE.text_secondary,
    });
  }
}

function renderDivider(slide, el) {
  slide.addShape(SHAPES.LINE, {
    x: el.x ?? 0.5,
    y: el.y ?? 2.5,
    w: el.w ?? 9,
    h: 0.01,
    line: { color: el.color ?? PALETTE.border, width: el.width ?? 0.5 },
  });
}

function renderIconText(slide, el) {
  const x = el.x ?? 0.5;
  const y = el.y ?? 1.5;
  const iconW = el.iconWidth ?? 0.35;
  const w = el.w ?? 4;
  const h = el.h ?? 0.35;

  // Icon/emoji character
  slide.addText(el.icon || "", {
    x: x, y: y, w: iconW, h: h,
    fontSize: el.iconFontSize ?? 14, fontFace: "Segoe UI Emoji",
    align: "center", valign: "middle",
  });

  // Text beside icon
  slide.addText(el.text || "", {
    x: x + iconW, y: y, w: w - iconW, h: h,
    fontSize: el.fontSize ?? 11, fontFace: el.fontFace ?? "Arial",
    color: el.color ?? PALETTE.text_dark,
    bold: el.bold ?? false,
    valign: "middle",
  });
}

// ── 슬라이드 렌더링 ──

function renderSlide(pres, slideData, slideNum, totalSlides) {
  const slide = pres.addSlide();
  const elements = slideData.elements || [];
  const bg = slideData.background;

  // 배경
  if (bg) {
    if (typeof bg === "string") {
      slide.background = { fill: bg };
    } else if (bg.fill) {
      slide.background = { fill: bg.fill };
    } else if (bg.gradient) {
      // pptxgenjs gradient 지원은 제한적이므로 단색 폴백
      slide.background = { fill: bg.gradient[0] || PALETTE.bg_dark };
    }
  }

  // 각 요소 렌더링
  for (const el of elements) {
    try {
      switch (el.type) {
        case "text":
          renderText(slide, el);
          break;
        case "table":
          renderTable(slide, el);
          break;
        case "chart":
          renderChart(slide, el);
          break;
        case "shape":
          renderShape(slide, el);
          break;
        case "kpi_card":
          renderKpiCard(slide, el);
          break;
        case "callout":
          renderCallout(slide, el);
          break;
        case "divider":
          renderDivider(slide, el);
          break;
        case "icon_text":
          renderIconText(slide, el);
          break;
        default:
          // 알 수 없는 타입은 텍스트로 폴백
          if (el.text) renderText(slide, el);
      }
    } catch (err) {
      console.error(`   ⚠ Element error on slide ${slideNum}: ${err.message}`);
    }
  }

  // 페이지 번호 (clean format, right-aligned)
  slide.addText(`${slideNum}`, {
    x: 9.0, y: 5.25, w: 0.8, h: 0.3,
    fontSize: 8, color: PALETTE.gray, fontFace: "Calibri", align: "right",
  });

  // Confidential footer
  if (slideData.confidential) {
    slide.addText("CONFIDENTIAL", {
      x: 0, y: 5.35, w: 10, h: 0.2,
      fontSize: 7, color: PALETTE.gray, fontFace: "Calibri",
      align: "center", italic: true,
    });
  }

  // 스피커 노트
  if (slideData.speaker_notes) {
    slide.addNotes(slideData.speaker_notes);
  }
}

// ── 메인 생성 함수 ──

function generateDynamicPresentation(outline, outputPath) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "GEMintern";
  pres.title = outline.deck_title || "Presentation";

  const slides = outline.slides || [];
  console.log(`\n🎨 Dynamic PPT: ${slides.length} slides`);
  console.log(`   Title: ${outline.deck_title || "Untitled"}\n`);

  for (let i = 0; i < slides.length; i++) {
    try {
      renderSlide(pres, slides[i], i + 1, slides.length);
      console.log(`   ✓ Slide ${i + 1}: ${slides[i].title || "—"} (${(slides[i].elements || []).length} elements)`);
    } catch (err) {
      console.error(`   ✗ Slide ${i + 1}: ${err.message}`);
    }
  }

  pres.writeFile({ fileName: outputPath })
    .then(() => {
      console.log(`\n✅ Saved: ${outputPath} (${fs.statSync(outputPath).size} bytes)`);
    })
    .catch(err => {
      console.error(`\n❌ Error: ${err.message}`);
      process.exit(1);
    });
}

// ── CLI ──
if (require.main === module) {
  const [jsonPath, outPath] = process.argv.slice(2);
  if (!jsonPath || !outPath) {
    console.log("Usage: node generate_pptx_dynamic.js <outline.json> <output.pptx>");
    process.exit(1);
  }
  const outline = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  generateDynamicPresentation(outline, outPath);
}

module.exports = { generateDynamicPresentation, PALETTE };
