from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.config import settings
from app.db.database import get_db
from app.db.models import FileModel, MeasurementModel, FileStatus
from app.schemas.file import FileUploadResponse, FileMetadataResponse, FileMeasurementsResponse, FeatureMeasurement
from app.utils.file_utils import validate_file_extension, validate_and_save_upload
from app.services.file_processor import FileProcessorService

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a geospatial file (.kml or .zip containing a Shapefile).
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload request."
        )

    file_type = validate_file_extension(file.filename)
    
    # Create DB record in UPLOADED status
    file_record = FileModel(
        filename=file.filename,
        file_type=file_type,
        status=FileStatus.UPLOADED
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    # Save path: uploads/{id}/{filename}
    saved_path = settings.UPLOAD_DIR / file_record.id / file.filename
    
    try:
        validate_and_save_upload(file, saved_path)
    except HTTPException as e:
        file_record.status = FileStatus.FAILED
        file_record.error_message = e.detail
        db.commit()
        raise e

    # Process file synchronously
    file_record = FileProcessorService.process_file(file_record, saved_path, db)

    return file_record

@router.get("/{file_id}/", response_model=FileMetadataResponse)
def get_file_metadata(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    Get metadata and processing status of an uploaded file.
    """
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found."
        )
    return file_record

@router.get("/{file_id}/measurements/", response_model=FileMeasurementsResponse)
def get_file_measurements(
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    Get measurements for features in the uploaded file.
    """
    file_record = db.query(FileModel).filter(FileModel.id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found."
        )

    if file_record.status == FileStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File processing failed: {file_record.error_message}"
        )

    measurements = (
        db.query(MeasurementModel)
        .filter(MeasurementModel.file_id == file_id)
        .order_by(MeasurementModel.feature_id.asc())
        .all()
    )

    return FileMeasurementsResponse(
        file_id=file_id,
        measurements=[FeatureMeasurement.model_validate(m) for m in measurements]
    )
