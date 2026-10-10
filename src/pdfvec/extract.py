"""PDF 페이지에서 텍스트를 추출합니다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


def extract_pages(path: str | Path) -> list[PageText]:
    """페이지 번호(1부터)와 텍스트를 반환합니다.

    PyMuPDF로 읽고, 실패하거나 글자가 없으면 pypdf로 다시 읽습니다.
    """
    pdf_path = Path(path)
    try:
        pages = _extract_pymupdf(pdf_path)
    except Exception:
        pages = _extract_pypdf(pdf_path)
    else:
        if not any(page.text.strip() for page in pages):
            pages = _extract_pypdf(pdf_path)
    return [page for page in pages if page.text.strip()]


def _extract_pymupdf(path: Path) -> list[PageText]:
    import pymupdf

    document = pymupdf.open(path)
    try:
        return [
            PageText(page=index, text=page.get_text("text") or "")
            for index, page in enumerate(document, start=1)
        ]
    finally:
        document.close()


def _extract_pypdf(path: Path) -> list[PageText]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [
        PageText(page=index, text=page.extract_text() or "")
        for index, page in enumerate(reader.pages, start=1)
    ]
