"""한국어 문장 경계를 기준으로 겹치는 청크를 만듭니다."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from pdfvec.extract import PageText

DEFAULT_CHUNK_SIZE = 400
DEFAULT_OVERLAP = 80

# 긴 어미를 먼저 두고, 소수점(9.6)은 문장 경계로 보지 않습니다.
_BOUNDARY = re.compile(
    r"(?:"
    r"습니까|했습니까|였습니다|했습니다|입니다|습니다|합니다|했어요|"
    r"일까요|할까요|인가요|세요|이죠|이에요|예요|에요|요|까|죠|네|다"
    r")[.!?…]+"
    r"|(?<!\d)[.!?。！？…]+"
    r"(?=\s|$)"
)


@dataclass(frozen=True)
class Chunk:
    file: str
    page: int
    chunk_id: str
    text: str
    sha256: str
    file_sha256: str


def normalize_text(text: str) -> str:
    """줄바꿈과 연속 공백을 한 칸으로 맞추고 NFC로 정규화합니다."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """마침표와 한국어 문장 종결 뒤에서 문장을 나눕니다."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    sentences: list[str] = []
    start = 0
    for match in _BOUNDARY.finditer(normalized):
        end = match.end()
        while end < len(normalized) and normalized[end].isspace():
            end += 1
        piece = normalized[start:end].strip()
        if piece:
            sentences.append(piece)
        start = end
    tail = normalized[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """문장 경계에 맞춰 자르고, 다음 청크가 앞 청크의 끝을 겹쳐 갖게 합니다."""
    if chunk_size <= 0:
        raise ValueError("chunk_size는 1 이상이어야 합니다.")
    if overlap < 0:
        raise ValueError("overlap은 0 이상이어야 합니다.")
    if overlap >= chunk_size:
        raise ValueError("overlap은 chunk_size보다 작아야 합니다.")

    normalized = normalize_text(text)
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        hard_end = min(start + chunk_size, length)
        end = hard_end if hard_end == length else _snap_end(normalized, start, hard_end)
        if end <= start:
            end = hard_end
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = start + 1
        next_start = _snap_start(normalized, next_start, low=start + 1, high=end)
        if next_start <= start or next_start >= end:
            next_start = min(end, start + max(1, chunk_size - overlap))
        if next_start <= start:
            next_start = start + 1
        start = next_start
    return chunks


def chunk_pages(
    pages: list[PageText],
    *,
    file: str,
    file_sha256: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """페이지를 넘지 않고 청크를 만듭니다. 같은 본문은 SHA-256으로 한 번만 남깁니다."""
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for page in pages:
        parts = chunk_text(page.text, chunk_size=chunk_size, overlap=overlap)
        for index, part in enumerate(parts):
            digest = chunk_sha256(file, page.page, part)
            if digest in seen:
                continue
            seen.add(digest)
            chunks.append(
                Chunk(
                    file=file,
                    page=page.page,
                    chunk_id=f"{file}:p{page.page}:c{index}",
                    text=part,
                    sha256=digest,
                    file_sha256=file_sha256,
                )
            )
    return chunks


def chunk_sha256(file: str, page: int, text: str) -> str:
    payload = f"{file}\0{page}\0{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _snap_end(text: str, start: int, hard_end: int) -> int:
    """청크 후반부에서 문장 경계, 없으면 공백을 찾습니다."""
    window_lo = start + max(1, (hard_end - start) // 2)
    best: int | None = None
    for match in _BOUNDARY.finditer(text[start:hard_end]):
        candidate = start + match.end()
        while candidate < hard_end and text[candidate].isspace():
            candidate += 1
        if window_lo <= candidate <= hard_end:
            best = candidate
    if best is not None:
        return best
    space = text.rfind(" ", window_lo, hard_end)
    if space != -1:
        return space + 1
    return hard_end


def _snap_start(text: str, pos: int, *, low: int, high: int) -> int:
    """겹침 시작점을 단어나 문장 경계로 당깁니다."""
    window_lo = max(low, pos - 40)
    best: int | None = None
    for match in _BOUNDARY.finditer(text[window_lo : pos + 1]):
        candidate = window_lo + match.end()
        while candidate < high and text[candidate].isspace():
            candidate += 1
        if low <= candidate <= pos:
            best = candidate
    if best is not None:
        return best
    space = text.rfind(" ", window_lo, pos + 1)
    if space != -1 and low <= space + 1 <= pos:
        return space + 1
    return pos
