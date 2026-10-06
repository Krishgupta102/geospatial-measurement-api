import logging
from typing import Dict, Any, Optional
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)

class MeasurementService:
    @staticmethod
    def calculate_feature_measurement(geom: Optional[BaseGeometry]) -> Dict[str, Any]:
        """
        Calculates area or length for a given Shapely geometry.
        
        Returns dict:
            {
                "geometry_type": str,
                "measurement_type": "area" | "length" | "none" | "unsupported",
                "value": Optional[float],
                "unit": Optional[str]
            }
        """
        if geom is None or geom.is_empty:
            return {
                "geometry_type": "Empty",
                "measurement_type": "none",
                "value": None,
                "unit": None
            }

        geom_type = geom.geom_type

        try:
            if geom_type in ("Polygon", "MultiPolygon"):
                area_sq_meters = float(geom.area)
                return {
                    "geometry_type": geom_type,
                    "measurement_type": "area",
                    "value": round(area_sq_meters, 2),
                    "unit": "square_meters"
                }
            elif geom_type in ("LineString", "MultiLineString"):
                length_meters = float(geom.length)
                return {
                    "geometry_type": geom_type,
                    "measurement_type": "length",
                    "value": round(length_meters, 2),
                    "unit": "meters"
                }
            elif geom_type in ("Point", "MultiPoint"):
                return {
                    "geometry_type": geom_type,
                    "measurement_type": "none",
                    "value": None,
                    "unit": None
                }
            else:
                logger.warning(f"Unsupported geometry type encountered: '{geom_type}'")
                return {
                    "geometry_type": geom_type,
                    "measurement_type": "unsupported",
                    "value": None,
                    "unit": None
                }
        except Exception as e:
            logger.error(f"Error calculating measurement for geometry {geom_type}: {e}")
            return {
                "geometry_type": geom_type,
                "measurement_type": "unsupported",
                "value": None,
                "unit": None
            }
