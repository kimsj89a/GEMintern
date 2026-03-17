/**
 * TypeScript interfaces matching backend Pydantic models (api_models.py).
 * Used by api/client.ts for request parameter typing.
 */

// --- Request types (matching backend Pydantic models) ---

export interface GenerateRequest {
  project_name: string;
  template_option?: string;
  thinking_level?: string;
  file_context?: string;
  inputs?: Record<string, unknown>;
  mode?: string;
}

export interface QaRequest {
  project_name?: string;
  question: string;
  selected_docs?: string[];
  file_context?: string;
}

export interface AnalysisRequest {
  task_type: string;
  project_name?: string;
  file_context?: string;
  kwargs?: Record<string, unknown>;
}

export interface SettingsData {
  api_key?: string;
  model_name?: string;
  anthropic_api_key?: string;
  thinking_level?: string;
  api_key_configured?: boolean;
  anthropic_api_key_configured?: boolean;
  [key: string]: unknown;
}

// --- Slide types ---

export interface SlideTable {
  headers: string[];
  rows: (string | number)[][];
}

export interface SlideChart {
  chart_type?: string;
  categories?: string[];
  series?: { name?: string; values: number[] }[];
}

export interface SlideMetric {
  label?: string;
  value?: string | number;
  sub?: string;
  color?: string;
}

export interface SlideBanner {
  label?: string;
  text?: string;
}

export interface SlideColumnData {
  title?: string;
  name?: string;
  items?: string[];
  table?: SlideTable;
}

export interface SlideRisk {
  category?: string;
  title?: string;
  severity?: string;
  level?: string;
  description?: string;
  text?: string;
}

export interface SlideTimelineNode {
  title?: string;
  label?: string;
  description?: string;
}

export interface SlideBlock {
  number?: string;
  title?: string;
  description?: string;
}

export interface SlideCard {
  title?: string;
  subtitle?: string;
  items?: string[];
}

export interface SlideElement {
  kind?: string;
  text?: string;
  value?: string;
  label?: string;
  role?: string;
  bold?: boolean;
  fill?: string;
  shape_type?: string;
}

export interface SlideData {
  slide_type?: string;
  type?: string;
  title?: string;
  subtitle?: string;
  layout_hint?: string;
  elements?: SlideElement[];
  // NP template fields
  table?: SlideTable;
  chart?: SlideChart;
  metrics?: SlideMetric[];
  kpi_cards?: SlideMetric[];
  risks?: SlideRisk[];
  items?: (SlideRisk | SlideTimelineNode | string)[];
  nodes?: (SlideTimelineNode | string)[];
  steps?: (SlideTimelineNode | string)[];
  left?: SlideColumnData;
  right?: SlideColumnData;
  left_column?: SlideColumnData;
  right_column?: SlideColumnData;
  banner?: SlideBanner;
  source?: string;
  section_number?: string;
  verdict?: string;
  conclusion?: string;
  content?: string;
  blocks?: SlideBlock[];
  cards?: SlideCard[];
}
