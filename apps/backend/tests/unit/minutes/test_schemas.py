"""MIN-103: schema validation for MinuteCreateRequest (R3-001 title max_length)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.minutes.schemas import MinuteCreateRequest


def test_title_accepts_200_chars() -> None:
    m = MinuteCreateRequest(title="x" * 200)
    assert len(m.title) == 200


def test_title_rejects_over_200_chars() -> None:
    with pytest.raises(ValidationError):
        MinuteCreateRequest(title="x" * 201)
