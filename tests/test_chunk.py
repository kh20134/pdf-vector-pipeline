import pytest

from pdfvec.chunk import chunk_sha256, chunk_text, split_sentences


def test_decimal_is_not_a_sentence_boundary():
    text = "백록담까지 약 9.6킬로미터입니다. 왕복은 9시간입니다."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert "9.6킬로미터" in sentences[0]
    assert sentences[1].startswith("왕복은")


def test_korean_endings_split_sentences():
    text = "입산은 오전 5시 30분에 시작합니다. 낮 12시에 마감합니다."
    sentences = split_sentences(text)
    assert sentences == [
        "입산은 오전 5시 30분에 시작합니다.",
        "낮 12시에 마감합니다.",
    ]


def test_wrapped_pdf_lines_join_into_one_sentence():
    text = "한라산 국립공원은\n제주도 한가운데에 있습니다."
    assert split_sentences(text) == ["한라산 국립공원은 제주도 한가운데에 있습니다."]


def test_short_text_is_one_chunk():
    assert chunk_text("성산일출봉은 유네스코 세계자연유산입니다.") == [
        "성산일출봉은 유네스코 세계자연유산입니다."
    ]


def test_empty_text():
    assert chunk_text("  \n\t ") == []
    assert split_sentences("") == []


def test_unbroken_hangul_keeps_size_and_exact_overlap():
    text = "가" * 200
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert chunks[0] == "가" * 50
    assert all(len(chunk) <= 50 for chunk in chunks)
    assert len(chunks) > 1
    for previous, following in zip(chunks, chunks[1:]):
        assert following.startswith(previous[-10:])


def test_sentence_chunks_share_a_tail():
    sentence = "성판악 탐방로 입산은 오전 5시 30분에 시작합니다. "
    text = sentence * 12
    chunks = chunk_text(text, chunk_size=80, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)
    for previous, following in zip(chunks, chunks[1:]):
        assert _shared_suffix_prefix(previous, following) >= 10


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("문장입니다.", chunk_size=10, overlap=10)


def test_sha256_changes_with_page_and_text():
    first = chunk_sha256("a.pdf", 1, "안녕")
    assert first == chunk_sha256("a.pdf", 1, "안녕")
    assert first != chunk_sha256("a.pdf", 2, "안녕")
    assert first != chunk_sha256("b.pdf", 1, "안녕")
    assert len(first) == 64


def _shared_suffix_prefix(left: str, right: str) -> int:
    shared = 0
    limit = min(len(left), len(right))
    for size in range(1, limit + 1):
        if left[-size:] == right[:size]:
            shared = size
    return shared
