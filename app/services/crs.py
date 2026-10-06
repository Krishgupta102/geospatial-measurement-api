import logging
import geopandas as gpd
from pyproj import CRS

logger = logging.getLogger(__name__)

class MissingCRSException(Exception):
    """Raised when geospatial data is missing CRS information."""
    pass

class CRSService:
    @staticmethod
    def get_crs_string(gdf: gpd.GeoDataFrame) -> str:
        """Returns string representation of the GeoDataFrame's CRS."""
        if gdf.crs is None:
            return "UNKNOWN"
        return gdf.crs.to_string()

    @staticmethod
    def prepare_projected_gdf(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        """
        Validates the input GeoDataFrame CRS and converts it to an appropriate projected CRS if necessary.
        Returns tuple of (projected_gdf, original_crs_str).
        
        CRS Strategy:
        1. If CRS is missing (None), raise MissingCRSException.
        2. If CRS is geographic (e.g. EPSG:4326 - lat/lon in degrees), estimate an appropriate local projected
           CRS (UTM) using estimate_utm_crs() and transform the GeoDataFrame using to_crs().
        3. If CRS is already projected, return it directly.
        """
        if gdf.crs is None:
            raise MissingCRSException(
                "Geospatial file does not specify a Coordinate Reference System (CRS). "
                "Cannot perform spatial measurements without a known CRS."
            )

        original_crs_str = gdf.crs.to_string()

        # If CRS is geographic (degrees / angular coordinates)
        if gdf.crs.is_geographic:
            try:
                # GeoPandas estimate_utm_crs calculates local UTM zone based on dataset bounding box
                utm_crs = gdf.estimate_utm_crs()
                logger.info(f"Geographic CRS '{original_crs_str}' detected. Reprojecting to estimated UTM CRS '{utm_crs}'.")
                projected_gdf = gdf.to_crs(utm_crs)
                return projected_gdf, original_crs_str
            except Exception as e:
                logger.warning(f"Failed to estimate UTM CRS for dataset: {e}. Falling back to World Equidistant Cylindrical (EPSG:4087).")
                fallback_crs = CRS.from_epsg(4087)
                projected_gdf = gdf.to_crs(fallback_crs)
                return projected_gdf, original_crs_str

        # If CRS is already projected (e.g., UTM or state plane in linear meters/feet)
        return gdf, original_crs_str
