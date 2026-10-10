"""samples/jeju_guide.pdf 를 다시 만듭니다. 나눔고딕이 설치되어 있어야 합니다."""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
FONT = Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")
OUTPUT = ROOT / "samples" / "jeju_guide.pdf"

PAGES = [
    (
        "한라산 탐방 안내",
        [
            "한라산 국립공원은 제주도 한가운데에 있습니다. 가장 많이 이용하는 성판악 코스는 해발 750미터에서 시작하여 백록담까지 편도 9.6킬로미터입니다. 걸어서 왕복하면 약 9시간이 걸립니다.",
            "성판악 탐방로 입산은 오전 5시 30분에 시작하고, 낮 12시에 입산을 마감합니다. 하산은 오후 3시까지 성판악 통제소를 통과해야 합니다. 겨울에는 아이젠과 방한복을 준비합니다.",
            "관음사 코스는 해발 600미터의 관음사 야영장에서 출발합니다. 편도 8.7킬로미터이고 경사가 가파릅니다. 초보자는 성판악 코스를 권장합니다.",
        ],
    ),
    (
        "성산일출봉과 우도",
        [
            "성산일출봉은 유네스코 세계자연유산입니다. 입장 시간은 매일 오전 7시부터 오후 8시까지입니다. 성인 입장료는 5,000원이고, 청소년은 2,500원입니다. 정상 분화구까지는 도보로 약 30분이 걸립니다.",
            "일출을 보려면 개장 시각에 맞춰 입장하는 것이 좋습니다. 정상의 분화구 둘레를 한 바퀴 도는 데는 20분 정도가 걸립니다.",
            "우도는 성산포항에서 여객선으로 15분이면 도착합니다. 첫배는 오전 8시에 뜨고 막배는 오후 5시에 출항합니다. 우도에서는 땅콩 아이스크림과 해안 산책로가 알려져 있습니다.",
        ],
    ),
]


def main() -> None:
    if not FONT.is_file() or not FONT_BOLD.is_file():
        raise SystemExit(f"나눔고딕 폰트가 없습니다: {FONT}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open()
    for title, paragraphs in PAGES:
        page = document.new_page(width=595, height=842)
        page.insert_font(fontname="ng", fontfile=str(FONT))
        page.insert_font(fontname="ngb", fontfile=str(FONT_BOLD))
        title_left = page.insert_textbox(
            pymupdf.Rect(56, 52, 539, 100),
            title,
            fontname="ngb",
            fontsize=20,
            color=(0.12, 0.16, 0.28),
        )
        body_left = page.insert_textbox(
            pymupdf.Rect(56, 118, 539, 780),
            "\n\n".join(paragraphs),
            fontname="ng",
            fontsize=12,
            color=(0.1, 0.1, 0.1),
            align=pymupdf.TEXT_ALIGN_JUSTIFY,
        )
        if title_left < 0 or body_left < 0:
            raise SystemExit(f"페이지에 글이 넘쳤습니다: {title}")
    document.set_metadata({"title": "제주 탐방 안내", "author": "pdf-vector-pipeline"})
    document.subset_fonts()
    document.save(OUTPUT, garbage=4, deflate=True)
    document.close()
    print(OUTPUT)


if __name__ == "__main__":
    main()
