"""Test fixtures for scrivener-mcp."""

from pathlib import Path

import pytest

from scrivener_mcp.parser import ScrivxParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_PROJECT = FIXTURES_DIR / "TestProject.scriv"


@pytest.fixture
def scriv_path():
    return TEST_PROJECT


@pytest.fixture
def parser(scriv_path):
    return ScrivxParser(scriv_path)
