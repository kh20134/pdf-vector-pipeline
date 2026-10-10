from pdfvec.cli import main, wrap_display
from pdfvec.embed import build_embedder
from tests.fakes import FakeEmbedder


def test_cli_ingest_search_and_second_ingest_skips(tmp_path, sample_pdf, monkeypatch, capsys):
    def fake_embedder(provider=None, model=None):
        return FakeEmbedder()

    monkeypatch.setattr("pdfvec.cli.build_embedder", fake_embedder)
    monkeypatch.setattr("pdfvec.pipeline.build_embedder", fake_embedder)
    database = tmp_path / "chroma"
    assert main(["ingest", str(sample_pdf), "--persist-dir", str(database)]) == 0
    ingested = capsys.readouterr().out
    assert "인제스트 완료" in ingested
    assert "SHA-256:" in ingested
    assert "추가:" in ingested
    assert "samples/jeju_guide.pdf" in ingested

    assert main(["search", "성산일출봉 입장", "--persist-dir", str(database), "--top-k", "2"]) == 0
    found = capsys.readouterr().out
    assert "성산일출봉" in found
    assert "페이지 2" in found
    assert ":p2:c" in found

    assert main(["ingest", str(sample_pdf), "--persist-dir", str(database)]) == 0
    again = capsys.readouterr().out
    assert "추가: 0" in again
    assert "중복 건너뜀:" in again


def test_cli_missing_file_and_bad_overlap(tmp_path, sample_pdf, capsys):
    assert main(["ingest", str(tmp_path / "missing.pdf")]) == 1
    error = capsys.readouterr().err
    assert "PDF" in error

    assert main(["ingest", str(sample_pdf), "--chunk-size", "10", "--overlap", "10"]) == 1


def test_wrap_breaks_on_spaces():
    text = "성산일출봉은 유네스코 유산입니다."
    lines = wrap_display(text, width=24, indent="    ")
    assert [line.strip() for line in lines] == ["성산일출봉은", "유네스코 유산입니다."]
    assert all(line.startswith("    ") for line in lines)


def test_help_exits_zero():
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("help should exit")


def test_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PDFVEC_EMBEDDING_PROVIDER", "openai")
    try:
        build_embedder(None)
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("missing key should fail")


def test_unknown_provider():
    try:
        build_embedder("nope")
    except ValueError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("unknown provider should fail")
