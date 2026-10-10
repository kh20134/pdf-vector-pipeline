"""PDF 텍스트를 청크와 임베딩으로 바꿔 Chroma에 저장하고 검색합니다."""

__version__ = "0.1.0"

from pdfvec.pipeline import ingest_pdf, search

__all__ = ["__version__", "ingest_pdf", "search"]
