import pytest
import zipfile
import tempfile
from pathlib import Path
from fastapi import HTTPException
from app.utils.file_utils import safe_extract_zip

def test_zip_path_traversal_prevention():
    """Verify that a ZIP file attempting path traversal (Zip Slip) is rejected."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        bad_zip = tmp_path / "bad.zip"
        
        # Create a malicious ZIP containing ../../malicious.txt
        with zipfile.ZipFile(bad_zip, "w") as zf:
            zf.writestr("../../malicious.txt", "hacked")

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        with pytest.raises(HTTPException) as exc_info:
            safe_extract_zip(bad_zip, extract_dir)

        assert exc_info.value.status_code == 400
        assert "path traversal vulnerability" in exc_info.value.detail.lower()
