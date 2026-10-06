from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class FileUploadResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    feature_count: int
    crs: Optional[str] = None
    created_at: datetime
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class FileMetadataResponse(FileUploadResponse):
    pass

class FeatureMeasurement(BaseModel):
    feature_id: int
    geometry_type: str
    measurement_type: str
    value: Optional[float] = None
    unit: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class FileMeasurementsResponse(BaseModel):
    file_id: str
    measurements: List[FeatureMeasurement]
