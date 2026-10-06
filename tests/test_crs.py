import pytest
import geopandas as gpd
from shapely.geometry import Polygon
from app.services.crs import CRSService, MissingCRSException

def test_geographic_crs_transformation():
    # Polygon around Bangalore coordinates (EPSG:4326)
    poly = Polygon([(77.5946, 12.9716), (77.5956, 12.9716), (77.5956, 12.9726), (77.5946, 12.9726)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")

    projected_gdf, original_crs = CRSService.prepare_projected_gdf(gdf)

    assert original_crs == "EPSG:4326"
    assert projected_gdf.crs.is_projected is True
    assert "32643" in projected_gdf.crs.to_string()  # UTM Zone 43N for South India
    # Verify calculated area is ~12,000 m² (not 0.000001 deg²)
    calculated_area = projected_gdf.geometry.iloc[0].area
    assert 10000 < calculated_area < 15000

def test_missing_crs_handling():
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf_nocrs = gpd.GeoDataFrame(geometry=[poly], crs=None)

    with pytest.raises(MissingCRSException) as exc_info:
        CRSService.prepare_projected_gdf(gdf_nocrs)
    
    assert "does not specify a Coordinate Reference System" in str(exc_info.value)

def test_already_projected_crs():
    poly = Polygon([(500000, 1430000), (501000, 1430000), (501000, 1431000), (500000, 1431000)])
    gdf_proj = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:32643")

    projected_gdf, original_crs = CRSService.prepare_projected_gdf(gdf_proj)

    assert original_crs == "EPSG:32643"
    assert projected_gdf.crs.to_string() == "EPSG:32643"
    assert projected_gdf.crs.is_projected is True
