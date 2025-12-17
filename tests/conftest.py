import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def temp_db_path(tmp_path):
    """Garante que cada teste use um banco isolado fora do repositório."""
    db_path = tmp_path / "restaurante.db"
    os.environ["RESTAURANTE_DB_PATH"] = str(db_path)
    yield db_path
