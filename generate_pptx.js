/**
 * generate_pptx.js — Stage 4: PPT Generation from JSON Outline
 *
 * Usage:
 *   node src/generate_pptx.js outline.json output.pptx
 *
 * 핵심 로직:
 * 1. JSON 아웃라인 로드
 * 2. 각 slide의 slide_type에 매핑되는 renderer 호출
 * 3. pptxgenjs로 .pptx 파일 생성
 *
 * 참고 GitHub:
 * - CyberTimon/Powerpointer-For-Local-LLMs (LLM → pptxgenjs 파이프라인)
 * - mynavitechtus-dungbt/power-point-generate-by-ollama (JSON → pptx 패턴)
 * - presenton/presenton (구조화된 JSON → pptx)
 */

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const { SLIDE_RENDERERS, PALETTE } = require("./slide_masters.js");

// ═══════════════════════════════════════════
//  Main Generation Function
// ═══════════════════════════════════════════

function generatePresentation(outline, outputPath) {
  const pres = new pptxgen();

  // Presentation metadata
  pres.layout = "LAYOUT_16x9";
  pres.author = "RAG-IB Pipeline";
  pres.title = outline.deck_title || "Investment Presentation";
  pres.subject = outline.subtitle || "";

  const slides = outline.slides || [];
  const totalSlides = slides.length;

  console.log(`\n🔨 Generating ${totalSlides} slides...`);
  console.log(`   Title: ${outline.deck_title || "Untitled"}`);
  console.log(`   Theme: Midnight Executive\n`);

  slides.forEach((slideData, idx) => {
    const slideType = slideData.slide_type || "_default";
    const renderer = SLIDE_RENDERERS[slideType] || SLIDE_RENDERERS._default;
    const slideNum = idx + 1;

    try {
      renderer(pres, slideData, slideNum, totalSlides);
      console.log(`   ✓ Slide ${slideNum}: [${slideType}] ${slideData.title || "—"}`);
    } catch (err) {
      console.error(`   ✗ Slide ${slideNum}: [${slideType}] Error: ${err.message}`);
      // Fallback: render as default
      try {
        SLIDE_RENDERERS._default(pres, slideData, slideNum, totalSlides);
        console.log(`   ↳ Fallback rendered for slide ${slideNum}`);
      } catch (fallbackErr) {
        console.error(`   ↳ Fallback also failed: ${fallbackErr.message}`);
      }
    }
  });

  // Speaker notes
  slides.forEach((slideData, idx) => {
    if (slideData.speaker_notes) {
      try {
        const slide = pres.slides[idx];
        if (slide) {
          slide.addNotes(slideData.speaker_notes);
        }
      } catch (_) {
        // notes 추가 실패는 무시
      }
    }
  });

  // Write file
  const outputDir = path.dirname(outputPath);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  pres.writeFile({ fileName: outputPath })
    .then(() => {
      console.log(`\n✅ Presentation saved: ${outputPath}`);
      console.log(`   Slides: ${totalSlides}`);
      console.log(`   Size: ${fs.statSync(outputPath).size} bytes`);
    })
    .catch((err) => {
      console.error(`\n❌ Error writing file: ${err.message}`);
      process.exit(1);
    });
}


// ═══════════════════════════════════════════
//  CLI Entry Point
// ═══════════════════════════════════════════

if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.log("Usage: node generate_pptx.js <outline.json> <output.pptx>");
    console.log("");
    console.log("Example:");
    console.log("  node src/generate_pptx.js output/outline.json output/deck.pptx");
    process.exit(1);
  }

  const [outlinePath, outputPath] = args;

  // Load outline
  if (!fs.existsSync(outlinePath)) {
    console.error(`Error: Outline file not found: ${outlinePath}`);
    process.exit(1);
  }

  const outlineRaw = fs.readFileSync(outlinePath, "utf8");
  let outline;
  try {
    outline = JSON.parse(outlineRaw);
  } catch (err) {
    console.error(`Error: Invalid JSON in ${outlinePath}: ${err.message}`);
    process.exit(1);
  }

  console.log("╔═══════════════════════════════════════╗");
  console.log("║   RAG → IB PPT Pipeline — Stage 4    ║");
  console.log("╚═══════════════════════════════════════╝");

  generatePresentation(outline, outputPath);
}

module.exports = { generatePresentation };
