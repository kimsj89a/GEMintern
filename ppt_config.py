"""
config.py — Pipeline configuration
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineConfig:
    """전체 파이프라인 설정"""

    # ── Paths ──
    data_dir: Path = Path("data")
    output_dir: Path = Path("output")
    chroma_dir: Path = Path(".chroma_db")

    # ── Ingestion ──
    supported_formats: list = field(
        default_factory=lambda: [".pdf", ".docx", ".pptx", ".txt", ".md", ".html"]
    )

    # ── Chunking ──
    chunk_strategy: str = "semantic"        # "semantic" | "fixed" | "recursive"
    chunk_size: int = 800                   # tokens (fixed/recursive 전용)
    chunk_overlap: int = 100                # tokens overlap
    semantic_min_chunk: int = 200           # semantic 최소 청크 크기
    semantic_max_chunk: int = 1500          # semantic 최대 청크 크기

    # ── Embedding ──
    embedding_model: str = "text-embedding-3-small"  # OpenAI
    embedding_dim: int = 1536

    # ── Retrieval ──
    retrieval_top_k: int = 15               # 검색 결과 수
    retrieval_rerank: bool = True           # 재순위화 여부
    rerank_top_k: int = 8                   # 재순위 후 최종 결과 수

    # ── LLM (Outline Generation) ──
    llm_provider: str = "anthropic"         # "anthropic" | "openai"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 8000

    # ── PPT Generation ──
    pptx_layout: str = "LAYOUT_16x9"
    pptx_theme: str = "midnight_executive"  # color palette name

    # ── API Keys (from env) ──
    @property
    def anthropic_api_key(self) -> Optional[str]:
        return os.getenv("ANTHROPIC_API_KEY")

    @property
    def openai_api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")


# ── IB Slide Type Definitions ──
SLIDE_TYPES = {
    "cover": "표지 슬라이드 (딜명, 날짜, 회사로고)",
    "toc": "목차",
    "executive_summary": "Executive Summary (핵심 투자 하이라이트)",
    "company_overview": "회사 개요 (사업 모델, 연혁, 조직)",
    "market_analysis": "시장 분석 (TAM/SAM/SOM, 경쟁 구도)",
    "financial_summary": "재무 요약 (매출, 영업이익, EBITDA 추이)",
    "financial_projection": "재무 전망 (매출 예측, 수익성 전망)",
    "valuation": "밸류에이션 (DCF, Comps, 멀티플)",
    "deal_structure": "딜 구조 (투자 조건, RCPS 구조, 주요 조항)",
    "risk_factors": "리스크 요인 (사업/시장/규제/구조적 리스크)",
    "kpi_dashboard": "KPI 대시보드 (핵심 지표 카드)",
    "comparison_table": "비교 테이블 (경쟁사 분석, 시리즈 비교)",
    "timeline": "타임라인 (연혁, 마일스톤, 로드맵)",
    "key_metrics": "핵심 지표 (Big Number 카드 레이아웃)",
    "text_heavy": "본문 중심 슬라이드 (DD 결과, 논의사항)",
    "closing": "마무리 슬라이드 (Q&A, 연락처)",
}

# ── Color Palettes ──
COLOR_PALETTES = {
    "midnight_executive": {
        "primary": "1E2761",
        "secondary": "CADCFC",
        "accent": "F96167",
        "bg_dark": "0F1535",
        "bg_light": "F8F9FC",
        "text_dark": "1A1A2E",
        "text_light": "FFFFFF",
        "chart_colors": ["1E2761", "3D5A99", "6B8BC4", "F96167", "F9E795", "2C5F2D"],
    },
    "ocean_gradient": {
        "primary": "065A82",
        "secondary": "1C7293",
        "accent": "21295C",
        "bg_dark": "031D30",
        "bg_light": "F0F7FA",
        "text_dark": "0A2540",
        "text_light": "FFFFFF",
        "chart_colors": ["065A82", "1C7293", "21295C", "4ECDC4", "FFE66D", "FF6B6B"],
    },
    "charcoal_minimal": {
        "primary": "36454F",
        "secondary": "F2F2F2",
        "accent": "FF6B35",
        "bg_dark": "212121",
        "bg_light": "FAFAFA",
        "text_dark": "212121",
        "text_light": "FFFFFF",
        "chart_colors": ["36454F", "607D8B", "90A4AE", "FF6B35", "FFA726", "66BB6A"],
    },
}
