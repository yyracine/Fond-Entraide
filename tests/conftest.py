import sqlite3
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
REF_DB = BASE_DIR / "cotisations.db"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "reference_db: test nécessitant la base de référence cotisations.db",
    )


@pytest.fixture(scope="session")
def con():
    if not REF_DB.exists():
        pytest.skip(f"Base de référence introuvable : {REF_DB}")
    c = sqlite3.connect(f"file:{REF_DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    yield c
    c.close()


@pytest.fixture(scope="session")
def db_path():
    return REF_DB