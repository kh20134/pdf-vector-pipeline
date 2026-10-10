"""Chroma 영구 저장소. 청크 아이디는 SHA-256입니다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings

from pdfvec.chunk import Chunk


@dataclass(frozen=True)
class SearchHit:
    score: float
    file: str
    page: int
    chunk_id: str
    text: str
    sha256: str


class ChromaStore:
    def __init__(self, persist_dir: str | Path, collection: str = "pdfs") -> None:
        self.persist_dir = str(persist_dir)
        self.collection_name = collection
        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection,
            embedding_function=None,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return int(self._collection.count())

    def metadata_for_file(self, file: str) -> list[dict]:
        found = self._collection.get(where={"file": file}, include=["metadatas"])
        return [dict(item) for item in (found["metadatas"] or [])]

    def delete_file(self, file: str) -> None:
        found = self._collection.get(where={"file": file}, include=[])
        ids = list(found["ids"] or [])
        if ids:
            self._collection.delete(ids=ids)

    def add(self, chunks: list[Chunk], embeddings: list[list[float]], model_name: str) -> tuple[int, int]:
        if len(chunks) != len(embeddings):
            raise ValueError("청크 수와 임베딩 수가 다릅니다.")
        if not chunks:
            return 0, 0
        self.ensure_model(model_name)
        existing = set(self._collection.get(ids=[chunk.sha256 for chunk in chunks], include=[])["ids"])
        new_indexes: list[int] = []
        seen: set[str] = set()
        for index, chunk in enumerate(chunks):
            if chunk.sha256 in existing or chunk.sha256 in seen:
                continue
            seen.add(chunk.sha256)
            new_indexes.append(index)
        if not new_indexes:
            return 0, len(chunks)
        try:
            self._collection.add(
                ids=[chunks[index].sha256 for index in new_indexes],
                documents=[chunks[index].text for index in new_indexes],
                embeddings=[embeddings[index] for index in new_indexes],
                metadatas=[_metadata(chunks[index], model_name) for index in new_indexes],
            )
        except Exception as exc:
            _reraise_dimension(exc)
        return len(new_indexes), len(chunks) - len(new_indexes)

    def query(self, embedding: list[float], top_k: int) -> list[SearchHit]:
        total = self.count()
        if total == 0 or top_k <= 0:
            return []
        try:
            found = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, total),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            _reraise_dimension(exc)
        hits: list[SearchHit] = []
        documents = found["documents"][0]
        metadatas = found["metadatas"][0]
        distances = found["distances"][0]
        for text, meta, distance in zip(documents, metadatas, distances):
            info = dict(meta or {})
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            hits.append(
                SearchHit(
                    score=score,
                    file=str(info.get("file", "")),
                    page=int(info.get("page", 0)),
                    chunk_id=str(info.get("chunk_id", "")),
                    text=text or "",
                    sha256=str(info.get("sha256", "")),
                )
            )
        return hits

    def ensure_model(self, model_name: str) -> None:
        found = self._collection.get(limit=1, include=["metadatas"])
        if not found["ids"]:
            return
        previous = (found["metadatas"][0] or {}).get("embedding_model")
        if previous and previous != model_name:
            raise RuntimeError(
                "임베딩 모델이 기존 컬렉션과 다릅니다. "
                "다른 --persist-dir 또는 --collection을 지정하세요. "
                f"(저장됨: {previous}, 요청: {model_name})"
            )

    def all_metadata(self) -> list[dict]:
        found = self._collection.get(include=["metadatas"])
        return [dict(item) for item in (found["metadatas"] or [])]


def _metadata(chunk: Chunk, model_name: str) -> dict:
    return {
        "file": chunk.file,
        "page": chunk.page,
        "chunk_id": chunk.chunk_id,
        "sha256": chunk.sha256,
        "file_sha256": chunk.file_sha256,
        "embedding_model": model_name,
    }


def _reraise_dimension(exc: Exception) -> None:
    if "dimension" in str(exc).lower():
        raise RuntimeError(
            "임베딩 차원이 컬렉션과 맞지 않습니다. 다른 --persist-dir 또는 --collection을 지정하세요."
        ) from exc
    raise exc
