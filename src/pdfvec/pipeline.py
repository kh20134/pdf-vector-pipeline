"""PDF 인제스트와 검색을 한 흐름으로 묶습니다."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pdfvec.chunk import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, chunk_pages
from pdfvec.embed import Embedder, build_embedder
from pdfvec.extract import extract_pages
from pdfvec.store import ChromaStore, SearchHit

DEFAULT_PERSIST_DIR = ".chroma"
DEFAULT_COLLECTION = "pdfs"


@dataclass(frozen=True)
class IngestResult:
    file: str
    file_sha256: str
    pages: int
    chunks: int
    added: int
    skipped: int
    persist_dir: str
    collection: str
    provider: str
    model: str


def display_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.name


def ingest_pdf(
    path: str | Path,
    *,
    persist_dir: str | Path = DEFAULT_PERSIST_DIR,
    collection: str = DEFAULT_COLLECTION,
    embedder: Embedder | None = None,
    provider: str | None = None,
    model: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    store: ChromaStore | None = None,
) -> IngestResult:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    embedder = embedder or build_embedder(provider, model)
    chroma = store or ChromaStore(persist_dir, collection)
    file_label = display_path(pdf_path)
    file_sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    existing = chroma.metadata_for_file(file_label)
    if existing and all(item.get("file_sha256") == file_sha256 for item in existing):
        chroma.ensure_model(embedder.model_name)
        pages = len({int(item.get("page", 0)) for item in existing})
        return IngestResult(
            file=file_label,
            file_sha256=file_sha256,
            pages=pages,
            chunks=len(existing),
            added=0,
            skipped=len(existing),
            persist_dir=chroma.persist_dir,
            collection=chroma.collection_name,
            provider=embedder.provider,
            model=embedder.model_name,
        )
    if existing:
        chroma.delete_file(file_label)
    pages = extract_pages(pdf_path)
    chunks = chunk_pages(
        pages,
        file=file_label,
        file_sha256=file_sha256,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    if not chunks:
        raise ValueError("추출된 텍스트가 없습니다.")
    embeddings = embedder.embed_documents([chunk.text for chunk in chunks])
    added, skipped = chroma.add(chunks, embeddings, embedder.model_name)
    return IngestResult(
        file=file_label,
        file_sha256=file_sha256,
        pages=len({page.page for page in pages}),
        chunks=len(chunks),
        added=added,
        skipped=skipped,
        persist_dir=chroma.persist_dir,
        collection=chroma.collection_name,
        provider=embedder.provider,
        model=embedder.model_name,
    )


def search(
    query: str,
    *,
    persist_dir: str | Path = DEFAULT_PERSIST_DIR,
    collection: str = DEFAULT_COLLECTION,
    embedder: Embedder | None = None,
    provider: str | None = None,
    model: str | None = None,
    top_k: int = 5,
    store: ChromaStore | None = None,
) -> list[SearchHit]:
    text = query.strip()
    if not text:
        raise ValueError("검색어가 비어 있습니다.")
    if top_k < 1:
        raise ValueError("top_k는 1 이상이어야 합니다.")
    embedder = embedder or build_embedder(provider, model)
    chroma = store or ChromaStore(persist_dir, collection)
    chroma.ensure_model(embedder.model_name)
    return chroma.query(embedder.embed_query(text), top_k)
