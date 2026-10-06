from fastapi import status
from shapely.geometry import GeometryCollection, Point
from app.services.measurement import MeasurementService

def test_get_measurements_valid_kml(client, sample_data_dir):
    file_path = sample_data_dir / "valid.kml"
    with open(file_path, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("valid.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    file_id = upload_resp.json()["id"]

    resp = client.get(f"/api/files/{file_id}/measurements/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["file_id"] == file_id
    measurements = data["measurements"]
    assert len(measurements) == 3

    # Feature 0: Polygon -> area
    poly_m = measurements[0]
    assert poly_m["feature_id"] == 0
    assert poly_m["geometry_type"] in ("Polygon", "MultiPolygon")
    assert poly_m["measurement_type"] == "area"
    assert poly_m["unit"] == "square_meters"
    assert poly_m["value"] > 0

    # Feature 1: LineString -> length
    line_m = measurements[1]
    assert line_m["feature_id"] == 1
    assert line_m["geometry_type"] in ("LineString", "MultiLineString")
    assert line_m["measurement_type"] == "length"
    assert line_m["unit"] == "meters"
    assert line_m["value"] > 0

    # Feature 2: Point -> none
    pt_m = measurements[2]
    assert pt_m["feature_id"] == 2
    assert pt_m["geometry_type"] in ("Point", "MultiPoint")
    assert pt_m["measurement_type"] == "none"
    assert pt_m["unit"] is None
    assert pt_m["value"] is None

def test_get_measurements_not_found(client):
    resp = client.get("/api/files/non-existent-uuid/measurements/")
    assert resp.status_code == status.HTTP_404_NOT_FOUND

def test_get_measurements_failed_file(client, sample_data_dir):
    file_path = sample_data_dir / "missing_crs_shapefile.zip"
    with open(file_path, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("missing_crs_shapefile.zip", f, "application/zip")}
        )
    file_id = upload_resp.json()["id"]

    resp = client.get(f"/api/files/{file_id}/measurements/")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "processing failed" in resp.json()["detail"].lower()

def test_measurement_service_unsupported_geometry():
    geomcoll = GeometryCollection([Point(0, 0)])
    result = MeasurementService.calculate_feature_measurement(geomcoll)
    assert result["geometry_type"] == "GeometryCollection"
    assert result["measurement_type"] == "unsupported"
    assert result["value"] is None
    assert result["unit"] is None
