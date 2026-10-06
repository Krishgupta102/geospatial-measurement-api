import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.database import Base

class FileStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class FileModel(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # 'kml' or 'zip'
    status = Column(String(20), nullable=False, default=FileStatus.UPLOADED)
    feature_count = Column(Integer, default=0)
    crs = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    error_message = Column(Text, nullable=True)

    measurements = relationship("MeasurementModel", back_populates="file", cascade="all, delete-orphan")

class MeasurementModel(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(36), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    feature_id = Column(Integer, nullable=False)
    geometry_type = Column(String(50), nullable=False)
    measurement_type = Column(String(20), nullable=False)  # 'area', 'length', 'none', 'unsupported'
    value = Column(Float, nullable=True)  # area in sq meters, length in meters, or None
    unit = Column(String(30), nullable=True)  # 'square_meters', 'meters', or None

    file = relationship("FileModel", back_populates="measurements")
