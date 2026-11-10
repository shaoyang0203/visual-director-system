"""Writable temporary folders for tests.

`tempfile.mkdtemp` creates 0o700 directories that some confined Windows hosts
then refuse to write into. When PA_TEST_TMP points at a normal writable folder,
this helper creates an ordinary folder there and cleans it up.
"""
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def tempdir(prefix="pa-test-"):
    base = os.environ.get("PA_TEST_TMP")
    if base:
        root = Path(base)
        root.mkdir(parents=True, exist_ok=True)
        folder = root / (prefix + uuid.uuid4().hex[:10])
        folder.mkdir()
    else:
        folder = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)
