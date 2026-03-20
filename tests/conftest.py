from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

LOCAL_TMP = ROOT / ".pytest_tmp"
LOCAL_TMP.mkdir(exist_ok=True)
local_tmp_str = str(LOCAL_TMP)
os.environ["TMP"] = local_tmp_str
os.environ["TEMP"] = local_tmp_str
os.environ["TMPDIR"] = local_tmp_str


@pytest.fixture
def tmp_path() -> Path:
    return Path(tempfile.mkdtemp(dir=local_tmp_str))
