from pdfvec.extract import extract_pages


def test_pymupdf_and_pypdf_read_korean(sample_pdf):
    from pdfvec.extract import _extract_pypdf, _extract_pymupdf

    for reader in (_extract_pymupdf, _extract_pypdf):
        text = "\n".join(page.text for page in reader(sample_pdf))
        assert "한라산" in text
        assert "성판악" in text
        assert "9.6" in text
        assert "성산일출봉" in text
        assert "우도" in text


def test_extract_pages_are_numbered_from_one(sample_pdf):
    pages = extract_pages(sample_pdf)
    assert [page.page for page in pages] == [1, 2]
    assert "성산일출봉" in pages[1].text
    assert "성산일출봉" not in pages[0].text


def test_falls_back_to_pypdf_when_pymupdf_fails(monkeypatch, sample_pdf):
    def boom(path):
        raise RuntimeError("pymupdf failed")

    monkeypatch.setattr("pdfvec.extract._extract_pymupdf", boom)
    pages = extract_pages(sample_pdf)
    assert any("성산일출봉" in page.text for page in pages)
