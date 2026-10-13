"""Unit check for the public clock helper used to save UTC timestamps."""
from datetime import timedelta, timezone
import pytest
from app import utc_now

pytestmark = pytest.mark.unit


def test_utc_now_returns_timezone_aware_utc():
    now = utc_now()
    assert now.tzinfo is timezone.utc
    assert now.utcoffset() == timedelta(0)
