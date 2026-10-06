import zipfile
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

def validate_file_extension(filename: str) -> str:
    """Validates file extension against allowed types (.kml, .zip)."""
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
        )
    return ext.lstrip(".")

def validate_and_save_upload(file: UploadFile, destination_path: Path) -> int:
    """
    Saves uploaded file chunk-by-chunk to destination_path while enforcing max size limit.
    """
    file_size = 0
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(destination_path, "wb") as out_file:
            while chunk := file.file.read(8192):
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE_BYTES:
                    out_file.close()
                    destination_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE_BYTES / (1024 * 1024):.1f} MB."
                    )
                out_file.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        destination_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save uploaded file: {str(e)}"
        )
    
    if file_size == 0:
        destination_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    return file_size

def safe_extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    """
    Safely extracts a ZIP file into extract_dir, preventing path traversal attacks.
    Returns path to the extracted .shp file.
    """
    if not zipfile.is_zipfile(zip_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded ZIP file is corrupted or not a valid ZIP archive."
        )

    target_dir = extract_dir.resolve()
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            # Security: Prevent Zip Slip / Path Traversal
            member_path = (target_dir / member.filename).resolve()
            if not str(member_path).startswith(str(target_dir)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Potential zip slip / path traversal vulnerability detected in ZIP archive."
                )
        
        zip_ref.extractall(target_dir)

    # Search for .shp file inside extracted directory (can be nested in folder)
    shp_files = list(target_dir.rglob("*.shp"))
    if not shp_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ZIP archive does not contain a valid Shapefile (.shp file)."
        )
    
    return shp_files[0]
