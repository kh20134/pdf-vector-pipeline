"""테스트용 결정적 임베더. 모델 파일을 받지 않습니다."""

from __future__ import annotations

import hashlib
import math


class FakeEmbedder:
    provider = "fake"
    model_name = "fake-hash"
    dim = 128

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        chars = [char.lower() for char in text if char.isalnum() or "가" <= char <= "힣"]
        grams: list[str] = []
        for size in (2, 3):
            grams.extend("".join(chars[index : index + size]) for index in range(len(chars) - size + 1))
        if not grams:
            grams = chars or ["empty"]
        for gram in grams:
            digest = hashlib.sha256(gram.encode("utf-8")).digest()
            bucket = digest[0] % self.dim
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
