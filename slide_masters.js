/**
 * slide_masters.js — IB Slide Master Templates
 *
 * 각 slide_type에 매핑되는 렌더링 함수 모음.
 * 디자인 원칙:
 * - 깔끔한 IB 스타일 (Midnight Executive 팔레트)
 * - 정보 밀도 높되, 여백 충분
 * - 차트/테이블은 pptxgenjs 네이티브 API 사용
 * - KPI 카드, 워터폴 등 IB 특화 레이아웃 포함
 */

const PALETTE = {
  primary: "1E2761",
  secondary: "CADCFC",
  accent: "F96167",
  bg_dark: "0F1535",
  bg_light: "F8F9FC",
  text_dark: "1A1A2E",
  text_light: "FFFFFF",
  chart_colors: ["1E2761", "3D5A99", "6B8BC4", "F96167", "F9E795", "2C5F2D"],
  gray: "8E8E93",
  border: "D1D5DB",
  card_bg: "FFFFFF",
};

const FONTS = {
  header: "Calibri",
  body: "Calibri Light",
  mono: "Consolas",
};

// ═══════════════════════════════════════════
//  Helper functions
// ═══════════════════════════════════════════

function addPageNumber(slide, num, total) {
  slide.addText(`${num} / ${total}`, {
    x: 9.0, y: 5.25, w: 0.8, h: 0.3,
    fontSize: 8, color: PALETTE.gray,
    fontFace: FONTS.body, align: "right",
  });
}

function addConfidentialBar(slide) {
  slide.addText("CONFIDENTIAL", {
    x: 0, y: 5.35, w: 10, h: 0.25,
    fontSize: 7, color: PALETTE.gray,
    fontFace: FONTS.body, align: "center",
    charSpacing: 3,
  });
}

function makeShadow() {
  return { type: "outer", blur: 4, offset: 2, angle: 135, color: "000000", opacity: 0.08 };
}

// ═══════════════════════════════════════════
//  Slide Renderers
// ═══════════════════════════════════════════

const SLIDE_RENDERERS = {

  // ── Cover ──
  cover(pres, slide_data, _idx, _total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_dark };

    // 좌측 악센트 바
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 0.06, h: 5.625, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};

    slide.addText(c.deal_name || slide_data.title || "Investment Memorandum", {
      x: 0.8, y: 1.5, w: 8.4, h: 1.2,
      fontSize: 36, fontFace: FONTS.header, color: PALETTE.text_light,
      bold: true, align: "left",
    });

    slide.addText(c.company_name || slide_data.subtitle || "", {
      x: 0.8, y: 2.8, w: 8.4, h: 0.6,
      fontSize: 20, fontFace: FONTS.body, color: PALETTE.secondary,
      align: "left",
    });

    // 날짜 & 작성자
    const meta_parts = [];
    if (c.date) meta_parts.push(c.date);
    if (c.prepared_by) meta_parts.push(`Prepared by ${c.prepared_by}`);
    if (meta_parts.length) {
      slide.addText(meta_parts.join("  |  "), {
        x: 0.8, y: 4.2, w: 8.4, h: 0.4,
        fontSize: 12, fontFace: FONTS.body, color: PALETTE.gray,
      });
    }

    slide.addText("CONFIDENTIAL", {
      x: 0.8, y: 4.8, w: 3, h: 0.3,
      fontSize: 9, fontFace: FONTS.body, color: PALETTE.accent,
      charSpacing: 4,
    });

    return slide;
  },

  // ── Executive Summary ──
  executive_summary(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Executive Summary", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary,
      bold: true, margin: 0,
    });

    // 구분선
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};

    // Key Metrics (상단 카드)
    const metrics = c.key_metrics || [];
    if (metrics.length > 0) {
      const cardW = Math.min(2.0, (9 / metrics.length) - 0.15);
      metrics.forEach((m, i) => {
        const x = 0.5 + i * (cardW + 0.15);
        slide.addShape(pres.shapes.RECTANGLE, {
          x, y: 1.1, w: cardW, h: 1.1,
          fill: { color: PALETTE.card_bg },
          shadow: makeShadow(),
        });
        slide.addText(m.value || "", {
          x, y: 1.15, w: cardW, h: 0.55,
          fontSize: 22, fontFace: FONTS.header, color: PALETTE.primary,
          bold: true, align: "center", valign: "middle", margin: 0,
        });
        const label_parts = [{ text: m.label || "", options: { fontSize: 10, color: PALETTE.gray, breakLine: true } }];
        if (m.change) {
          const changeColor = m.change.startsWith("+") ? "2C5F2D" : "F96167";
          label_parts.push({ text: m.change, options: { fontSize: 10, color: changeColor, bold: true } });
        }
        slide.addText(label_parts, {
          x, y: 1.7, w: cardW, h: 0.45,
          fontFace: FONTS.body, align: "center", valign: "top", margin: 0,
        });
      });
    }

    // Highlights (하단 불릿)
    const highlights = c.highlights || [];
    if (highlights.length > 0) {
      const bullets = highlights.map((h, i) => ({
        text: h,
        options: { bullet: true, breakLine: i < highlights.length - 1, fontSize: 13, color: PALETTE.text_dark },
      }));
      slide.addText(bullets, {
        x: 0.5, y: 2.5, w: 9, h: 2.8,
        fontFace: FONTS.body, paraSpaceAfter: 8, valign: "top",
      });
    }

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── Company Overview ──
  company_overview(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Company Overview", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};

    // 설명
    if (c.description) {
      slide.addText(c.description, {
        x: 0.5, y: 1.1, w: 9, h: 0.8,
        fontSize: 12, fontFace: FONTS.body, color: PALETTE.text_dark, valign: "top",
      });
    }

    // Key Facts (우측 카드)
    const facts = c.key_facts || [];
    if (facts.length) {
      facts.forEach((f, i) => {
        const y = 2.1 + i * 0.55;
        slide.addShape(pres.shapes.RECTANGLE, {
          x: 6.5, y, w: 3, h: 0.45,
          fill: { color: i % 2 === 0 ? "F0F2F8" : PALETTE.card_bg },
        });
        slide.addText(f.label || "", {
          x: 6.6, y, w: 1.2, h: 0.45,
          fontSize: 10, fontFace: FONTS.body, color: PALETTE.gray, valign: "middle", margin: 0,
        });
        slide.addText(f.value || "", {
          x: 7.8, y, w: 1.6, h: 0.45,
          fontSize: 11, fontFace: FONTS.header, color: PALETTE.text_dark, bold: true, valign: "middle", margin: 0,
        });
      });
    }

    // Business Segments
    const segs = c.business_segments || [];
    if (segs.length) {
      const segW = Math.min(2.8, 5.5 / segs.length - 0.15);
      segs.forEach((s, i) => {
        const x = 0.5 + i * (segW + 0.15);
        slide.addShape(pres.shapes.RECTANGLE, {
          x, y: 2.1, w: segW, h: 1.8,
          fill: { color: PALETTE.card_bg }, shadow: makeShadow(),
        });
        // 상단 악센트
        slide.addShape(pres.shapes.RECTANGLE, {
          x, y: 2.1, w: segW, h: 0.04,
          fill: { color: PALETTE.chart_colors[i % PALETTE.chart_colors.length] },
        });
        slide.addText(s.name || "", {
          x: x + 0.1, y: 2.2, w: segW - 0.2, h: 0.4,
          fontSize: 12, fontFace: FONTS.header, color: PALETTE.primary, bold: true, valign: "middle", margin: 0,
        });
        if (s.revenue_share) {
          slide.addText(s.revenue_share, {
            x: x + 0.1, y: 2.55, w: segW - 0.2, h: 0.3,
            fontSize: 18, fontFace: FONTS.header, color: PALETTE.accent, bold: true, margin: 0,
          });
        }
        if (s.description) {
          slide.addText(s.description, {
            x: x + 0.1, y: 2.85, w: segW - 0.2, h: 0.9,
            fontSize: 9, fontFace: FONTS.body, color: PALETTE.gray, valign: "top", margin: 0,
          });
        }
      });
    }

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── Financial Summary (with chart) ──
  financial_summary(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Financial Summary", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};
    const chartData = c.chart_data || {};

    // Chart
    if (chartData.labels && chartData.datasets) {
      const chartType = (c.chart_type || "bar").toLowerCase();
      const pptxChartType = chartType === "line" ? pres.charts.LINE : pres.charts.BAR;

      const datasets = chartData.datasets.map((ds, i) => ({
        name: ds.name || `Series ${i + 1}`,
        labels: chartData.labels,
        values: ds.values || [],
      }));

      slide.addChart(pptxChartType, datasets, {
        x: 0.5, y: 1.0, w: 5.5, h: 3.5,
        barDir: "col",
        chartColors: PALETTE.chart_colors.slice(0, datasets.length),
        chartArea: { fill: { color: PALETTE.card_bg }, roundedCorners: true },
        catAxisLabelColor: "64748B",
        valAxisLabelColor: "64748B",
        valGridLine: { color: "E2E8F0", size: 0.5 },
        catGridLine: { style: "none" },
        showValue: true,
        dataLabelPosition: "outEnd",
        dataLabelColor: PALETTE.text_dark,
        dataLabelFontSize: 9,
        showLegend: datasets.length > 1,
        legendPos: "b",
        legendFontSize: 9,
      });
    }

    // Key Metrics (우측)
    const metrics = c.key_metrics || [];
    metrics.forEach((m, i) => {
      const y = 1.0 + i * 0.75;
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 6.5, y, w: 3, h: 0.65,
        fill: { color: PALETTE.card_bg }, shadow: makeShadow(),
      });
      slide.addText(m.label || "", {
        x: 6.6, y, w: 1.8, h: 0.65,
        fontSize: 10, fontFace: FONTS.body, color: PALETTE.gray, valign: "middle", margin: 0,
      });
      slide.addText(m.value || "", {
        x: 8.2, y, w: 1.2, h: 0.65,
        fontSize: 14, fontFace: FONTS.header, color: PALETTE.primary, bold: true, valign: "middle", align: "right", margin: 0,
      });
    });

    // Footnotes
    const footnotes = c.footnotes || [];
    if (footnotes.length) {
      slide.addText(footnotes.map(f => `* ${f}`).join("\n"), {
        x: 0.5, y: 4.7, w: 9, h: 0.5,
        fontSize: 8, fontFace: FONTS.body, color: PALETTE.gray, italic: true,
      });
    }

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── KPI Dashboard ──
  kpi_dashboard(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Key Performance Indicators", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const metrics = (slide_data.content || {}).metrics || [];
    const cols = Math.min(metrics.length, 3);
    const rows = Math.ceil(metrics.length / cols);
    const cardW = (9 - (cols - 1) * 0.2) / cols;
    const cardH = Math.min(1.8, (4.2 - (rows - 1) * 0.2) / rows);

    metrics.forEach((m, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const x = 0.5 + col * (cardW + 0.2);
      const y = 1.1 + row * (cardH + 0.2);

      slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: cardH,
        fill: { color: PALETTE.card_bg }, shadow: makeShadow(),
      });

      // 상단 악센트
      const accentColor = PALETTE.chart_colors[i % PALETTE.chart_colors.length];
      slide.addShape(pres.shapes.RECTANGLE, {
        x, y, w: cardW, h: 0.04, fill: { color: accentColor },
      });

      // Label
      slide.addText(m.label || "", {
        x: x + 0.15, y: y + 0.1, w: cardW - 0.3, h: 0.3,
        fontSize: 11, fontFace: FONTS.body, color: PALETTE.gray, valign: "middle", margin: 0,
      });

      // Value
      slide.addText(m.value || "", {
        x: x + 0.15, y: y + 0.4, w: cardW - 0.3, h: 0.5,
        fontSize: 28, fontFace: FONTS.header, color: PALETTE.primary, bold: true, valign: "middle", margin: 0,
      });

      // Trend + Description
      const trend_text = [];
      if (m.trend) {
        const arrow = m.trend === "up" ? "▲" : m.trend === "down" ? "▼" : "─";
        const trendColor = m.trend === "up" ? "2C5F2D" : m.trend === "down" ? "F96167" : PALETTE.gray;
        trend_text.push({ text: arrow + " ", options: { color: trendColor, fontSize: 10 } });
      }
      if (m.description) {
        trend_text.push({ text: m.description, options: { color: PALETTE.gray, fontSize: 9 } });
      }
      if (trend_text.length) {
        slide.addText(trend_text, {
          x: x + 0.15, y: y + cardH - 0.4, w: cardW - 0.3, h: 0.3,
          fontFace: FONTS.body, valign: "bottom", margin: 0,
        });
      }
    });

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── Risk Factors ──
  risk_factors(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Risk Factors", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const risks = (slide_data.content || {}).risks || [];
    let yPos = 1.1;

    risks.forEach((category) => {
      // Category header
      slide.addText(category.category || "Risks", {
        x: 0.5, y: yPos, w: 9, h: 0.35,
        fontSize: 14, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
      });
      yPos += 0.4;

      // Risk items
      (category.items || []).forEach((item) => {
        const severityColor = item.severity === "High" ? "F96167" :
                              item.severity === "Medium" ? "F9E795" : "2C5F2D";

        // Severity badge
        slide.addShape(pres.shapes.RECTANGLE, {
          x: 0.5, y: yPos, w: 0.6, h: 0.35,
          fill: { color: severityColor },
        });
        slide.addText(item.severity || "?", {
          x: 0.5, y: yPos, w: 0.6, h: 0.35,
          fontSize: 7, fontFace: FONTS.body, color: PALETTE.text_light,
          align: "center", valign: "middle", bold: true, margin: 0,
        });

        // Risk text
        slide.addText(item.risk || "", {
          x: 1.2, y: yPos, w: 4.5, h: 0.35,
          fontSize: 11, fontFace: FONTS.body, color: PALETTE.text_dark, valign: "middle", margin: 0,
        });

        // Mitigation
        if (item.mitigation) {
          slide.addText(`→ ${item.mitigation}`, {
            x: 5.8, y: yPos, w: 3.7, h: 0.35,
            fontSize: 10, fontFace: FONTS.body, color: PALETTE.gray, valign: "middle", italic: true, margin: 0,
          });
        }

        yPos += 0.45;
      });

      yPos += 0.1;
    });

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── Comparison Table ──
  comparison_table(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Comparison", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};
    const headers = c.headers || [];
    const rows = c.rows || [];

    if (headers.length && rows.length) {
      const tableData = [
        headers.map(h => ({
          text: h,
          options: { fill: { color: PALETTE.primary }, color: PALETTE.text_light, bold: true, fontSize: 11 },
        })),
        ...rows.map((row, ri) =>
          row.map(cell => ({
            text: String(cell),
            options: {
              fill: { color: ri % 2 === 0 ? "F0F2F8" : PALETTE.card_bg },
              color: PALETTE.text_dark,
              fontSize: 10,
            },
          }))
        ),
      ];

      const colW = headers.map(() => 9 / headers.length);
      slide.addTable(tableData, {
        x: 0.5, y: 1.1, w: 9,
        colW,
        border: { pt: 0.5, color: PALETTE.border },
        fontFace: FONTS.body,
      });
    }

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── Deal Structure ──
  deal_structure(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Deal Structure", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};

    // Investment Amount 카드
    if (c.investment_amount) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0.5, y: 1.1, w: 3, h: 0.9, fill: { color: PALETTE.primary },
      });
      slide.addText("Investment Amount", {
        x: 0.6, y: 1.1, w: 2.8, h: 0.35,
        fontSize: 10, fontFace: FONTS.body, color: PALETTE.secondary, margin: 0,
      });
      slide.addText(c.investment_amount, {
        x: 0.6, y: 1.45, w: 2.8, h: 0.5,
        fontSize: 22, fontFace: FONTS.header, color: PALETTE.text_light, bold: true, margin: 0,
      });
    }

    // Instrument
    if (c.instrument) {
      slide.addShape(pres.shapes.RECTANGLE, {
        x: 3.7, y: 1.1, w: 2, h: 0.9, fill: { color: PALETTE.card_bg }, shadow: makeShadow(),
      });
      slide.addText("Instrument", {
        x: 3.8, y: 1.1, w: 1.8, h: 0.35,
        fontSize: 10, fontFace: FONTS.body, color: PALETTE.gray, margin: 0,
      });
      slide.addText(c.instrument, {
        x: 3.8, y: 1.45, w: 1.8, h: 0.5,
        fontSize: 16, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
      });
    }

    // Terms
    const terms = c.terms || [];
    if (terms.length) {
      const tableData = terms.map((t, i) => [
        { text: t.item || "", options: { fill: { color: i % 2 === 0 ? "F0F2F8" : PALETTE.card_bg }, bold: true, fontSize: 10, color: PALETTE.primary } },
        { text: t.detail || "", options: { fill: { color: i % 2 === 0 ? "F0F2F8" : PALETTE.card_bg }, fontSize: 10, color: PALETTE.text_dark } },
      ]);

      slide.addTable(tableData, {
        x: 0.5, y: 2.2, w: 9,
        colW: [2.5, 6.5],
        border: { pt: 0.5, color: PALETTE.border },
        fontFace: FONTS.body,
      });
    }

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── Timeline ──
  timeline(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Timeline", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const events = (slide_data.content || {}).events || [];
    if (events.length) {
      // 타임라인 중앙선
      const lineY = 3.0;
      slide.addShape(pres.shapes.LINE, {
        x: 0.5, y: lineY, w: 9, h: 0,
        line: { color: PALETTE.primary, width: 2 },
      });

      const spacing = 9 / Math.max(events.length, 1);
      events.forEach((e, i) => {
        const x = 0.5 + i * spacing + spacing / 2;

        // 점
        slide.addShape(pres.shapes.OVAL, {
          x: x - 0.1, y: lineY - 0.1, w: 0.2, h: 0.2,
          fill: { color: PALETTE.accent },
        });

        // 날짜 (위)
        slide.addText(e.date || "", {
          x: x - 0.7, y: lineY - 0.6, w: 1.4, h: 0.4,
          fontSize: 9, fontFace: FONTS.header, color: PALETTE.primary,
          bold: true, align: "center", margin: 0,
        });

        // 제목 (아래)
        slide.addText(e.title || "", {
          x: x - 0.7, y: lineY + 0.3, w: 1.4, h: 0.35,
          fontSize: 10, fontFace: FONTS.header, color: PALETTE.text_dark,
          bold: true, align: "center", margin: 0,
        });

        // 설명 (아래)
        if (e.description) {
          slide.addText(e.description, {
            x: x - 0.7, y: lineY + 0.65, w: 1.4, h: 0.6,
            fontSize: 8, fontFace: FONTS.body, color: PALETTE.gray,
            align: "center", margin: 0,
          });
        }
      });
    }

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },

  // ── Closing ──
  closing(pres, slide_data, _idx, _total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_dark };

    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 0.06, h: 5.625, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};

    slide.addText(c.message || "Thank You", {
      x: 0.8, y: 1.8, w: 8.4, h: 1,
      fontSize: 36, fontFace: FONTS.header, color: PALETTE.text_light,
      bold: true, align: "center",
    });

    // Contact info
    const contacts = c.contact || [];
    contacts.forEach((ct, i) => {
      const y = 3.2 + i * 0.5;
      const parts = [];
      if (ct.name) parts.push({ text: ct.name, options: { bold: true, color: PALETTE.text_light, fontSize: 12 } });
      if (ct.title) parts.push({ text: `  ${ct.title}`, options: { color: PALETTE.secondary, fontSize: 11 } });
      if (ct.email) parts.push({ text: `  ${ct.email}`, options: { color: PALETTE.gray, fontSize: 10 } });
      if (parts.length) {
        slide.addText(parts, {
          x: 0.8, y, w: 8.4, h: 0.4, fontFace: FONTS.body, align: "center",
        });
      }
    });

    slide.addText("CONFIDENTIAL", {
      x: 0.8, y: 4.8, w: 8.4, h: 0.3,
      fontSize: 9, fontFace: FONTS.body, color: PALETTE.accent,
      align: "center", charSpacing: 4,
    });

    return slide;
  },

  // ── Fallback: text_heavy / any unknown type ──
  _default(pres, slide_data, idx, total) {
    const slide = pres.addSlide();
    slide.background = { color: PALETTE.bg_light };

    slide.addText(slide_data.title || "Information", {
      x: 0.5, y: 0.3, w: 9, h: 0.5,
      fontSize: 24, fontFace: FONTS.header, color: PALETTE.primary, bold: true, margin: 0,
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 0.85, w: 2, h: 0.03, fill: { color: PALETTE.accent },
    });

    const c = slide_data.content || {};

    // Paragraphs
    const paras = c.paragraphs || [];
    if (paras.length) {
      slide.addText(paras.join("\n\n"), {
        x: 0.5, y: 1.1, w: 9, h: 2.5,
        fontSize: 12, fontFace: FONTS.body, color: PALETTE.text_dark, valign: "top",
      });
    }

    // Bullet points
    const bullets = c.bullet_points || c.highlights || [];
    if (bullets.length) {
      const bulletItems = bullets.map((b, i) => ({
        text: b,
        options: { bullet: true, breakLine: i < bullets.length - 1, fontSize: 12, color: PALETTE.text_dark },
      }));
      slide.addText(bulletItems, {
        x: 0.5, y: paras.length ? 3.8 : 1.1, w: 9, h: 2.0,
        fontFace: FONTS.body, paraSpaceAfter: 6, valign: "top",
      });
    }

    addPageNumber(slide, idx, total);
    addConfidentialBar(slide);
    return slide;
  },
};

// Map aliases
SLIDE_RENDERERS.market_analysis = SLIDE_RENDERERS._default;
SLIDE_RENDERERS.financial_projection = SLIDE_RENDERERS.financial_summary;
SLIDE_RENDERERS.valuation = SLIDE_RENDERERS._default;
SLIDE_RENDERERS.key_metrics = SLIDE_RENDERERS.kpi_dashboard;
SLIDE_RENDERERS.text_heavy = SLIDE_RENDERERS._default;
SLIDE_RENDERERS.toc = SLIDE_RENDERERS._default;

module.exports = { SLIDE_RENDERERS, PALETTE, FONTS };
