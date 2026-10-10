"""ingest / search 명령줄 인터페이스."""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import argparse
import shutil
import sys
import unicodedata
from pathlib import Path

from pdfvec import __version__
from pdfvec.chunk import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP
from pdfvec.embed import build_embedder, quiet_third_party_logs
from pdfvec.pipeline import DEFAULT_COLLECTION, DEFAULT_PERSIST_DIR, ingest_pdf, search


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdfvec",
        description="PDF를 청크로 나누어 임베딩하고 Chroma에서 검색합니다.",
    )
    parser.add_argument("--version", action="version", version=f"pdfvec {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="PDF를 추출·청킹·임베딩하여 저장합니다.")
    ingest.add_argument("pdf", type=Path, help="넣을 PDF 경로")
    ingest.add_argument("--persist-dir", default=DEFAULT_PERSIST_DIR, help="Chroma 저장 경로")
    ingest.add_argument("--collection", default=DEFAULT_COLLECTION, help="컬렉션 이름")
    ingest.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="청크 최대 글자 수")
    ingest.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="청크 사이 겹침 글자 수")
    ingest.add_argument("--provider", choices=["local", "openai"], default=None, help="임베딩 제공자")
    ingest.add_argument("--model", default=None, help="임베딩 모델 이름")

    query = commands.add_parser("search", help="저장된 청크를 의미 검색합니다.")
    query.add_argument("query", help="검색어")
    query.add_argument("--persist-dir", default=DEFAULT_PERSIST_DIR, help="Chroma 저장 경로")
    query.add_argument("--collection", default=DEFAULT_COLLECTION, help="컬렉션 이름")
    query.add_argument("--top-k", type=int, default=5, help="결과 개수")
    query.add_argument("--provider", choices=["local", "openai"], default=None, help="임베딩 제공자")
    query.add_argument("--model", default=None, help="임베딩 모델 이름")
    return parser


def main(argv: list[str] | None = None) -> int:
    quiet_third_party_logs()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            return _cmd_ingest(args)
        return _cmd_search(args)
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


def app() -> None:
    sys.exit(main())


def ingest_entry() -> None:
    sys.exit(main(["ingest", *sys.argv[1:]]))


def search_entry() -> None:
    sys.exit(main(["search", *sys.argv[1:]]))


def _cmd_ingest(args: argparse.Namespace) -> int:
    if args.chunk_size <= 0 or args.overlap < 0 or args.overlap >= args.chunk_size:
        raise ValueError("overlap은 0 이상이고 chunk_size보다 작아야 합니다.")
    result = ingest_pdf(
        args.pdf,
        persist_dir=args.persist_dir,
        collection=args.collection,
        provider=args.provider,
        model=args.model,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    print("인제스트 완료")
    print(f"파일: {result.file}")
    print(f"SHA-256: {result.file_sha256}")
    print(f"임베딩: {result.provider} ({result.model})")
    print(f"페이지: {result.pages}")
    print(f"청크: {result.chunks}")
    print(f"추가: {result.added}")
    print(f"중복 건너뜀: {result.skipped}")
    print(f"저장소: {result.persist_dir}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    if args.top_k < 1:
        raise ValueError("--top-k는 1 이상이어야 합니다.")
    embedder = build_embedder(args.provider, args.model)
    hits = search(
        args.query,
        persist_dir=args.persist_dir,
        collection=args.collection,
        embedder=embedder,
        top_k=args.top_k,
    )
    if not hits:
        print("검색 결과가 없습니다.")
        return 0
    width = max(40, shutil.get_terminal_size(fallback=(88, 24)).columns - 1)
    print(f"검색 결과 {len(hits)}건 · {embedder.provider} ({embedder.model_name})")
    print()
    for index, hit in enumerate(hits, start=1):
        print(f"[{index}] 유사도 {hit.score:.3f} · 페이지 {hit.page} · {hit.chunk_id}")
        print(f"    파일: {hit.file}")
        for line in wrap_display(" ".join(hit.text.split()), width, indent="    "):
            print(line)
        print()
    return 0


def wrap_display(text: str, width: int, indent: str = "") -> list[str]:
    """표시 폭 기준으로 줄바꿈합니다. 공백이 있으면 단어 중간에서 끊지 않습니다."""
    budget = max(8, width - display_width(indent))
    lines: list[str] = []
    current = ""
    current_width = 0
    for word in text.split(" "):
        word_width = display_width(word)
        extra = word_width + (1 if current else 0)
        if current and current_width + extra > budget:
            lines.append(indent + current)
            current = ""
            current_width = 0
        if word_width > budget:
            if current:
                lines.append(indent + current)
                current = ""
                current_width = 0
            lines.extend(indent + piece for piece in _wrap_long_word(word, budget))
            continue
        if current:
            current = f"{current} {word}"
            current_width += 1 + word_width
        else:
            current = word
            current_width = word_width
    if current:
        lines.append(indent + current)
    return lines or [indent]


def _wrap_long_word(word: str, budget: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    current_width = 0
    for char in word:
        char_width = 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
        if current and current_width + char_width > budget:
            pieces.append(current)
            current = char
            current_width = char_width
        else:
            current += char
            current_width += char_width
    if current:
        pieces.append(current)
    return pieces


def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1 for char in text)
