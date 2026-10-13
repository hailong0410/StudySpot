"""Disclosed staged CI failure; fix before any merge."""
import pytest
from domain import parse_filters

pytestmark = pytest.mark.unit


def test_staged_ci_filter_expectation():
    assert parse_filters("  library  ", "", "", "")["q"] == "wrong staged expectation"
