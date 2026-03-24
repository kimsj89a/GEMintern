"""
PPT Theme Configurations — IM/NP 테마 통합 설정
"""
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


class PptTheme:
    """Base theme configuration for PPT generation."""

    def __init__(self, name, aspect="4:3", **overrides):
        self.name = name
        self.aspect = aspect

        # Slide dimensions
        if aspect == "16:9":
            self.slide_width = Inches(13.333)
            self.slide_height = Inches(7.5)
        else:
            self.slide_width = Inches(10.0)
            self.slide_height = Inches(7.5)

        # Colors — defaults (overridable)
        self.color_primary = RGBColor(0x0C, 0x30, 0x64)    # Navy
        self.color_accent = RGBColor(0x00, 0x5D, 0xA2)     # Blue
        self.color_gold = RGBColor(0xCC, 0xA0, 0x00)       # Gold
        self.color_white = RGBColor(0xFF, 0xFF, 0xFF)
        self.color_black = RGBColor(0x00, 0x00, 0x00)
        self.color_dark_gray = RGBColor(0x40, 0x40, 0x40)
        self.color_mid_gray = RGBColor(0x88, 0x92, 0xA5)
        self.color_light_gray = RGBColor(0xD9, 0xDE, 0xE4)
        self.color_off_white = RGBColor(0xF5, 0xF6, 0xF8)
        self.color_red = RGBColor(0xC0, 0x00, 0x00)
        self.color_green = RGBColor(0x00, 0x80, 0x00)
        self.color_row_even = RGBColor(0xF2, 0xF6, 0xFA)
        self.color_row_odd = RGBColor(0xFF, 0xFF, 0xFF)

        # Fonts
        self.font_kr = "맑은 고딕"
        self.font_en = "Arial"
        self.font_heading = self.font_kr
        self.font_body = self.font_kr

        # Font sizes
        self.title_size = Pt(25)
        self.subtitle_size = Pt(12)
        self.header_size = Pt(15)
        self.body_title_size = Pt(14)
        self.body_size = Pt(11)
        self.note_size = Pt(9)

        # Apply overrides
        for k, v in overrides.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @property
    def chart_colors(self):
        return [
            self.color_primary, self.color_gold, self.color_accent,
            self.color_green, RGBColor(0x5B, 0x2C, 0x8C),
            RGBColor(0xD9, 0x77, 0x06),
        ]


# Pre-defined themes
NP_THEME = PptTheme(
    "NP",
    aspect="4:3",
    font_kr="맑은 고딕",
    font_en="Arial",
)

IM_THEME = PptTheme(
    "IM",
    aspect="custom",  # 11.93" × 8.50" NP IM 커스텀 비율
    font_kr="맑은 고딕",
    font_en="Arial",
    font_heading="Arial",
    font_body="Arial",
    title_size=Pt(24),
    subtitle_size=Pt(12),
    body_size=Pt(11),
    note_size=Pt(9),
)
# IM 테마는 커스텀 슬라이드 크기 사용
IM_THEME.slide_width = Inches(11.93)
IM_THEME.slide_height = Inches(8.50)

THEMES = {
    "np": NP_THEME,
    "im": IM_THEME,
}


def get_theme(name="np"):
    """Get a theme by name."""
    return THEMES.get(name.lower(), NP_THEME)
