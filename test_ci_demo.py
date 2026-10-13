"""Corrected test from the disclosed staged red-to-green CI demo."""
import pytest
from domain import parse_filters

pytestmark = pytest.mark.unit


def test_staged_ci_filter_expectation():
    assert parse_filters("  library  ", "", "", "")["q"] == "library"
