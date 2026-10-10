import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PDF = ROOT / "samples" / "jeju_guide.pdf"


@pytest.fixture
def sample_pdf() -> Path:
    assert SAMPLE_PDF.is_file(), "samples/jeju_guide.pdf 가 없습니다."
    return SAMPLE_PDF
