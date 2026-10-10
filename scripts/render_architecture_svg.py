"""한글을 윤곽선으로 넣어 docs/architecture.svg 를 만듭니다.

글자를 path로 굽기 때문에 보는 쪽에 한글 폰트가 없어도 그대로 보입니다.
"""

from __future__ import annotations

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
REGULAR = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
BOLD = Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
OUTPUT = ROOT / "docs" / "architecture.svg"

WIDTH = 1120
HEIGHT = 560


class Font:
    def __init__(self, path: Path) -> None:
        self.tt = TTFont(path)
        self.glyph_set = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upem = self.tt["head"].unitsPerEm
        self.ascent = self.tt["hhea"].ascent
        self.descent = self.tt["hhea"].descent

    def advance(self, char: str) -> int:
        name = self.cmap.get(ord(char))
        if name is None:
            return self.upem // 2
        return self.glyph_set[name].width

    def width(self, text: str, size: float) -> float:
        scale = size / self.upem
        return sum(self.advance(char) * scale for char in text)

    def paths(self, text: str, x: float, baseline: float, size: float, color: str) -> str:
        scale = size / self.upem
        parts: list[str] = []
        cursor = x
        for char in text:
            name = self.cmap.get(ord(char))
            advance = (self.glyph_set[name].width if name else self.upem // 2) * scale
            if name:
                pen = SVGPathPen(self.glyph_set)
                self.glyph_set[name].draw(pen)
                commands = pen.getCommands()
                if commands:
                    parts.append(
                        f'<path d="{commands}" fill="{color}" '
                        f'transform="translate({cursor:.2f} {baseline:.2f}) scale({scale:.6f} {-scale:.6f})"/>'
                    )
            cursor += advance
        return "\n".join(parts)


def centered(font: Font, text: str, box_x: float, box_w: float, baseline: float, size: float, color: str) -> str:
    text_width = font.width(text, size)
    x = box_x + (box_w - text_width) / 2
    return font.paths(text, x, baseline, size, color)


def main() -> None:
    regular = Font(REGULAR)
    bold = Font(BOLD)
    mid = (regular.ascent + regular.descent) / 2 / regular.upem

    def baseline(center_y: float, size: float) -> float:
        return center_y + mid * size

    chunks: list[str] = [
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#f4f6fb"/>',
        "<title>PDF 벡터 파이프라인</title>",
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        '<path d="M 0 1.2 L 8 5 L 0 8.8 Z" fill="#3b5bdb"/></marker></defs>',
    ]

    chunks.append(centered(bold, "PDF 벡터 파이프라인", 0, WIDTH, baseline(46, 26), 26, "#1b2430"))
    chunks.append(
        centered(
            regular,
            "추출  ·  한국어 청킹  ·  임베딩  ·  Chroma",
            0,
            WIDTH,
            baseline(82, 15),
            15,
            "#5c677a",
        )
    )

    box_w, box_h, gap = 184, 108, 28
    row1 = ["PDF 파일", "텍스트 추출", "한국어 청킹", "임베딩", "Chroma"]
    sub1 = ["원본 문서", "PyMuPDF · pypdf", "문장 경계 · 오버랩", "e5 · OpenAI", "SHA-256 중복 제거"]
    row1_w = len(row1) * box_w + (len(row1) - 1) * gap
    x1 = (WIDTH - row1_w) / 2
    y1 = 128
    accents = ["#3b5bdb", "#3b5bdb", "#3b5bdb", "#3b5bdb", "#0c8599"]
    draw_row(chunks, bold, regular, row1, sub1, x1, y1, box_w, box_h, gap, accents, baseline)

    row2 = ["검색 질의", "쿼리 임베딩", "유사도 검색", "결과"]
    sub2 = ["한국어 질문", "query 접두어", "코사인 거리", "파일 · 페이지 · 청크"]
    row2_w = len(row2) * box_w + (len(row2) - 1) * gap
    x2 = (WIDTH - row2_w) / 2
    y2 = 330
    draw_row(
        chunks,
        bold,
        regular,
        row2,
        sub2,
        x2,
        y2,
        box_w,
        box_h,
        gap,
        ["#6741d9", "#6741d9", "#6741d9", "#0c8599"],
        baseline,
    )

    chroma_cx = x1 + 4 * (box_w + gap) + box_w / 2
    search_cx = x2 + 2 * (box_w + gap) + box_w / 2
    y_join = y1 + box_h + 26
    chunks.append(
        f'<path d="M {chroma_cx:.1f} {y1 + box_h:.1f} V {y_join:.1f} H {search_cx:.1f} V {y2 - 2:.1f}" '
        f'fill="none" stroke="#0c8599" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#arrow)"/>'
    )

    chunks.append(
        centered(
            regular,
            "메타데이터   file   ·   page   ·   chunk_id",
            0,
            WIDTH,
            baseline(520, 15),
            15,
            "#3d4758",
        )
    )

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">\n'
        + "\n".join(chunks)
        + "\n</svg>\n"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(OUTPUT)


def draw_row(chunks, bold, regular, titles, subtitles, x, y, box_w, box_h, gap, accents, baseline) -> None:
    for index, (title, subtitle, accent) in enumerate(zip(titles, subtitles, accents)):
        left = x + index * (box_w + gap)
        clip = f"card{y:.0f}_{index}"
        chunks.append(
            f'<clipPath id="{clip}"><rect x="{left:.1f}" y="{y:.1f}" width="{box_w}" height="{box_h}" rx="14"/></clipPath>'
        )
        chunks.append(f'<g clip-path="url(#{clip})">')
        chunks.append(
            f'<rect x="{left:.1f}" y="{y:.1f}" width="{box_w}" height="{box_h}" fill="#ffffff"/>'
        )
        chunks.append(f'<rect x="{left:.1f}" y="{y:.1f}" width="6" height="{box_h}" fill="{accent}"/>')
        chunks.append("</g>")
        chunks.append(
            f'<rect x="{left:.1f}" y="{y:.1f}" width="{box_w}" height="{box_h}" rx="14" '
            f'fill="none" stroke="#d5dce8" stroke-width="1.4"/>'
        )
        chunks.append(centered(bold, title, left, box_w, baseline(y + 46, 16), 16, "#1b2430"))
        chunks.append(centered(regular, subtitle, left, box_w, baseline(y + 74, 12), 12, "#5c677a"))
        if index < len(titles) - 1:
            x1 = left + box_w + 4
            x2 = left + box_w + gap - 6
            mid_y = y + box_h / 2
            chunks.append(
                f'<line x1="{x1:.1f}" y1="{mid_y:.1f}" x2="{x2:.1f}" y2="{mid_y:.1f}" '
                f'stroke="#3b5bdb" stroke-width="1.6" marker-end="url(#arrow)"/>'
            )


if __name__ == "__main__":
    main()
