import pymupdf

from pdfvec.pipeline import ingest_pdf, search
from pdfvec.store import ChromaStore
from tests.fakes import FakeEmbedder


def test_metadata_and_dedup(tmp_path, sample_pdf):
    store = ChromaStore(tmp_path / "db", "pdfs")
    embedder = FakeEmbedder()
    first = ingest_pdf(sample_pdf, embedder=embedder, store=store)
    assert first.added > 0
    assert first.skipped == 0
    assert first.pages == 2
    assert first.file == "samples/jeju_guide.pdf"
    assert len(first.file_sha256) == 64

    metas = store.all_metadata()
    assert len(metas) == first.added
    for meta in metas:
        assert {"file", "page", "chunk_id"} <= set(meta)
        assert isinstance(meta["page"], int)
        assert meta["chunk_id"].startswith(f"{meta['file']}:p{meta['page']}:c")
        assert meta["sha256"]

    second = ingest_pdf(sample_pdf, embedder=embedder, store=store)
    assert second.added == 0
    assert second.skipped == first.added
    assert store.count() == first.added


def test_search_returns_seongsan_page(tmp_path, sample_pdf):
    store = ChromaStore(tmp_path / "db")
    embedder = FakeEmbedder()
    ingest_pdf(sample_pdf, embedder=embedder, store=store)
    hits = search("성산일출봉 입장 시간", embedder=embedder, store=store, top_k=3)
    assert hits
    assert hits[0].page == 2
    assert "성산일출봉" in hits[0].text
    assert hits[0].file.endswith("jeju_guide.pdf")
    assert hits[0].chunk_id.startswith("samples/jeju_guide.pdf:p2:c")
    assert hits[0].score > hits[-1].score or len(hits) == 1


def test_changed_pdf_replaces_old_chunks(tmp_path):
    pdf = tmp_path / "note.pdf"
    _write_pdf(pdf, "Hallasan trail opens at dawn.")
    store = ChromaStore(tmp_path / "db")
    embedder = FakeEmbedder()
    ingest_pdf(pdf, embedder=embedder, store=store)
    _write_pdf(pdf, "Seongsan Ilchulbong opens at seven.")
    again = ingest_pdf(pdf, embedder=embedder, store=store)
    assert again.added > 0
    hits = search("Seongsan Ilchulbong", embedder=embedder, store=store, top_k=5)
    blob = "\n".join(hit.text for hit in hits)
    assert "Seongsan" in blob
    assert "Hallasan" not in blob


def test_search_rejects_blank_query(tmp_path):
    store = ChromaStore(tmp_path / "db")
    try:
        search("   ", embedder=FakeEmbedder(), store=store)
    except ValueError as exc:
        assert "검색어" in str(exc)
    else:
        raise AssertionError("blank query should fail")


def _write_pdf(path, text: str) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text, fontsize=12, fontname="helv")
    document.save(path)
    document.close()
