"""로컬 E5 모델 또는 OpenAI로 임베딩을 만듭니다."""

from __future__ import annotations

import logging
import os
from typing import Protocol

DEFAULT_LOCAL_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"


class Embedder(Protocol):
    provider: str
    model_name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def quiet_third_party_logs() -> None:
    os.environ.setdefault("HF_HUB_VERBOSITY", "error")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    for name in (
        "huggingface_hub",
        "transformers",
        "sentence_transformers",
        "httpx",
        "httpcore",
        "chromadb",
        "urllib3",
    ):
        logging.getLogger(name).setLevel(logging.ERROR)
    try:
        from huggingface_hub.utils import logging as hub_logging

        hub_logging.set_verbosity_error()
    except Exception:
        return


def resolve_provider(provider: str | None) -> str:
    chosen = provider or os.environ.get("PDFVEC_EMBEDDING_PROVIDER", "local")
    return chosen.strip().lower()


def build_embedder(provider: str | None = None, model: str | None = None) -> Embedder:
    chosen = resolve_provider(provider)
    if chosen == "local":
        model_name = model or os.environ.get("PDFVEC_LOCAL_MODEL", DEFAULT_LOCAL_MODEL)
        return LocalE5Embedder(model_name)
    if chosen == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY가 없습니다. OpenAI 임베딩을 쓰려면 키를 설정하세요."
            )
        model_name = model or os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_MODEL)
        return OpenAIEmbedder(model_name)
    raise ValueError(f"알 수 없는 임베딩 제공자입니다: {chosen}")


class LocalE5Embedder:
    """intfloat/multilingual-e5 계열. 문서에는 passage:, 질의에는 query:를 붙입니다."""

    provider = "local"

    def __init__(self, model_name: str = DEFAULT_LOCAL_MODEL) -> None:
        quiet_third_party_logs()
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                'sentence-transformers가 없습니다. pip install -e ".[local]" 로 설치하거나 '
                "PDFVEC_EMBEDDING_PROVIDER=openai 를 사용하세요."
            ) from exc
        quiet_third_party_logs()
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            [f"passage: {text}" for text in texts],
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode(
            f"query: {text}",
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()


class OpenAIEmbedder:
    provider = "openai"

    def __init__(self, model_name: str = DEFAULT_OPENAI_MODEL) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                'openai 패키지가 없습니다. pip install -e ".[openai]" 로 설치하세요.'
            ) from exc
        self.model_name = model_name
        self._client = OpenAI()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 64):
            batch = texts[start : start + 64]
            response = self._client.embeddings.create(model=self.model_name, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend(item.embedding for item in ordered)
        return vectors
