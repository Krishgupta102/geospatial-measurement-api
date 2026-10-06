import logging
import tempfile
import fiona
import geopandas as gpd
from pathlib import Path
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import FileModel, MeasurementModel, FileStatus
from app.services.crs import CRSService, MissingCRSException
from app.services.measurement import MeasurementService
from app.utils.file_utils import safe_extract_zip

# Enable KML driver in Fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

logger = logging.getLogger(__name__)

class FileProcessorService:
    @staticmethod
    def process_file(file_record: FileModel, saved_file_path: Path, db: Session) -> FileModel:
        """
        Synchronously reads geospatial file, validates CRS, reprojects to projected CRS,
        computes measurements per feature, and stores metadata + measurements in DB.
        """
        file_record.status = FileStatus.PROCESSING
        db.commit()

        try:
            # 1. Load GeoDataFrame based on file type
            if file_record.file_type == "kml":
                try:
                    gdf = gpd.read_file(saved_file_path, driver="KML")
                except Exception as e:
                    try:
                        gdf = gpd.read_file(saved_file_path)
                    except Exception as inner_e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Malformed or invalid KML file: {str(e)}"
                        )
            elif file_record.file_type == "zip":
                with tempfile.TemporaryDirectory() as tmp_dir:
                    extract_path = Path(tmp_dir)
                    shp_path = safe_extract_zip(saved_file_path, extract_path)
                    try:
                        gdf = gpd.read_file(shp_path)
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Malformed or invalid Shapefile in ZIP archive: {str(e)}"
                        )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: '{file_record.file_type}'"
                )

            if gdf is None or gdf.empty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Geospatial file contains no features or valid records."
                )

            # 2. Check and handle CRS & reprojection
            projected_gdf, original_crs_str = CRSService.prepare_projected_gdf(gdf)
            file_record.crs = original_crs_str

            # 3. Calculate feature measurements
            measurements_to_insert = []
            valid_feature_count = 0

            for idx, row in projected_gdf.iterrows():
                geom = row.geometry
                measurement = MeasurementService.calculate_feature_measurement(geom)
                
                measurements_to_insert.append(
                    MeasurementModel(
                        file_id=file_record.id,
                        feature_id=int(idx),
                        geometry_type=measurement["geometry_type"],
                        measurement_type=measurement["measurement_type"],
                        value=measurement["value"],
                        unit=measurement["unit"]
                    )
                )
                valid_feature_count += 1

            # 4. Save measurements & update file status
            db.add_all(measurements_to_insert)
            file_record.feature_count = valid_feature_count
            file_record.status = FileStatus.COMPLETED
            db.commit()
            db.refresh(file_record)
            return file_record

        except HTTPException as e:
            # Re-raise HTTP validation exceptions so endpoint rejects malformed uploads with HTTP 400
            file_record.status = FileStatus.FAILED
            file_record.error_message = e.detail
            db.commit()
            raise e
        except MissingCRSException as e:
            logger.error(f"Processing failed for file {file_record.id}: {e}")
            file_record.status = FileStatus.FAILED
            file_record.error_message = str(e)
            db.commit()
            return file_record
        except Exception as e:
            logger.error(f"Processing failed for file {file_record.id}: {e}", exc_info=True)
            file_record.status = FileStatus.FAILED
            file_record.error_message = str(e)
            db.commit()
            return file_record
