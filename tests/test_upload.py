from pathlib import Path
from fastapi import status

def test_upload_valid_kml(client, sample_data_dir):
    file_path = sample_data_dir / "valid.kml"
    with open(file_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("valid.kml", f, "application/vnd.google-earth.kml+xml")}
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["filename"] == "valid.kml"
    assert data["file_type"] == "kml"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 3
    assert "EPSG:4326" in data["crs"]
    assert data["error_message"] is None

def test_upload_valid_shapefile(client, sample_data_dir):
    file_path = sample_data_dir / "valid_shapefile.zip"
    with open(file_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("valid_shapefile.zip", f, "application/zip")}
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["filename"] == "valid_shapefile.zip"
    assert data["file_type"] == "zip"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 2
    assert data["crs"] is not None

def test_upload_invalid_extension(client, sample_data_dir):
    file_path = sample_data_dir / "invalid.txt"
    with open(file_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("invalid.txt", f, "text/plain")}
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Unsupported file extension" in data["detail"]

def test_upload_malformed_zip(client, sample_data_dir):
    file_path = sample_data_dir / "malformed.zip"
    with open(file_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("malformed.zip", f, "application/zip")}
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Shapefile" in data["detail"]

def test_upload_missing_crs_zip(client, sample_data_dir):
    file_path = sample_data_dir / "missing_crs_shapefile.zip"
    with open(file_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("missing_crs_shapefile.zip", f, "application/zip")}
        )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "FAILED"
    assert "CRS" in data["error_message"]

def test_get_file_metadata_success(client, sample_data_dir):
    file_path = sample_data_dir / "valid.kml"
    with open(file_path, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("valid.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    file_id = upload_resp.json()["id"]

    get_resp = client.get(f"/api/files/{file_id}/")
    assert get_resp.status_code == status.HTTP_200_OK
    data = get_resp.json()
    assert data["id"] == file_id
    assert data["filename"] == "valid.kml"
    assert data["status"] == "COMPLETED"

def test_get_file_metadata_not_found(client):
    response = client.get("/api/files/non-existent-uuid/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()
