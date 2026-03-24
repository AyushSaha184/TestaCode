from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest


ROOT = Path(__file__).resolve().parent.parent
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

LOCAL_TMP = Path(tempfile.gettempdir()) / "ai-test-gen-pytest"
LOCAL_TMP.mkdir(exist_ok=True)
local_tmp_str = str(LOCAL_TMP)
os.environ["TMP"] = local_tmp_str
os.environ["TEMP"] = local_tmp_str
os.environ["TMPDIR"] = local_tmp_str

LOCAL_WORK_TMP = ROOT / ".pytest_tmp_runtime"
LOCAL_WORK_TMP.mkdir(exist_ok=True)


@pytest.fixture
def tmp_path() -> Path:
    path = LOCAL_WORK_TMP / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path
