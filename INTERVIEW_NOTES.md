# Interview Technical Notes: Geospatial File Measurement API

This document prepares you for technical interview discussions on the Geospatial File Measurement API. It covers every major architectural decision, geospatial concepts, security measures, and potential interview questions with recommended concise responses.

---

## Table of Contents
1. [Why FastAPI?](#1-why-fastapi)
2. [Why GeoPandas?](#2-why-geopandas)
3. [Why Shapely?](#3-why-shapely)
4. [How KML Processing Works](#4-how-kml-processing-works)
5. [How Shapefile ZIP Processing Works](#5-how-shapefile-zip-processing-works)
6. [How CRS Detection Works](#6-how-crs-detection-works)
7. [Why EPSG:4326 Cannot Directly Be Used for Measurements](#7-why-epsg4326-cannot-directly-be-used-for-measurements)
8. [How Projected CRS Selection Works](#8-how-projected-crs-selection-works)
9. [How Polygon Area is Calculated](#9-how-polygon-area-is-calculated)
10. [How LineString Length is Calculated](#10-how-linestring-length-is-calculated)
11. [How MultiPolygon / MultiLineString are Handled](#11-how-multipolygon--multilinestring-are-handled)
12. [How Invalid Files are Handled](#12-how-invalid-files-are-handled)
13. [How ZIP Path Traversal (Zip Slip) is Prevented](#13-how-zip-path-traversal-zip-slip-is-prevented)
14. [Why the Processing Model (Synchronous) Was Chosen](#14-why-the-processing-model-synchronous-was-chosen)
15. [Database Design](#15-database-design)
16. [API Design](#16-api-design)
17. [Testing Strategy](#17-testing-strategy)
18. [Potential Scalability Problems](#18-potential-scalability-problems)
19. [Modifications for Very Large Files](#19-modifications-for-very-large-files)
20. [Changes for Production Deployment](#20-changes-for-production-deployment)

---

### 1. Why FastAPI?
- **What the code does**: Uses FastAPI as the web framework to define asynchronous endpoints (`POST /api/files/`, `GET /api/files/{id}/`, `GET /api/files/{id}/measurements/`).
- **Why it does it**: FastAPI provides high performance (built on Starlette and Pydantic), automatic OpenAPI/Swagger documentation generation, native type-hinting validation, and easy dependency injection (`Depends(get_db)`).
- **What an interviewer might ask**: *"Why choose FastAPI over Flask or Django?"*
- **Concise answer**: *"FastAPI gives us automatic data validation with Pydantic, built-in Swagger documentation out of the box, high performance async capabilities, and cleaner dependency injection compared to Flask or Django, keeping our backend lightweight and maintainable."*

---

### 2. Why GeoPandas?
- **What the code does**: Uses `geopandas.read_file()` to load geospatial datasets into a unified DataFrame abstraction called a `GeoDataFrame`.
- **Why it does it**: GeoPandas abstracts away the complexity of parsing vector spatial formats (Shapefile, KML, GeoJSON) via GDAL/Fiona, handles CRS transformations cleanly via PyProj integration, and exposes vectorized geometry methods.
- **What an interviewer might ask**: *"Why use GeoPandas instead of parsing raw XML or using basic Shapefile readers?"*
- **Concise answer**: *"GeoPandas unifies vector dataset formats into tabular GeoDataFrames, handles complex spatial reprojections natively with PyProj (`to_crs()`), and integrates seamlessly with Shapely geometry objects."*

---

### 3. Why Shapely?
- **What the code does**: Processes feature geometries (computing `.area` and `.length`) using Shapely geometry primitives (`Polygon`, `MultiPolygon`, `LineString`, `Point`).
- **Why it does it**: Shapely is Python's standard library for planar geometry manipulation built on top of C++ GEOS library. It offers reliable, fast algorithms for planar spatial metrics.
- **What an interviewer might ask**: *"How does Shapely compute area and length under the hood?"*
- **Concise answer**: *"Shapely wraps the C++ GEOS library to compute planar 2D Cartesian spatial properties like polygon area via Green's theorem and linestring length via Euclidean distance."*

---

### 4. How KML Processing Works
- **What the code does**: Enables Fiona's KML driver (`fiona.drvsupport.supported_drivers['KML'] = 'rw'`) and reads KML placemarks with `gpd.read_file(saved_file_path, driver="KML")`.
- **Why it does it**: KML files are XML schemas specified by OGC. Fiona/GDAL parses XML elements (`<Placemark>`, `<Polygon>`, `<LineString>`) into spatial feature attributes and geometries.
- **What an interviewer might ask**: *"What challenges exist when parsing KML files?"*
- **Concise answer**: *"KML files frequently contain 3D coordinates (with Z altitude) and style metadata. Fiona parses the XML into Shapely geometries in WGS84 (EPSG:4326), from which we project to a metric CRS."*

---

### 5. How Shapefile ZIP Processing Works
- **What the code does**: Receives a `.zip` file, extracts members safely into a temporary directory, searches for the `.shp` file, and reads it with GeoPandas.
- **Why it does it**: ESRI Shapefiles consist of mandatory component files (`.shp` for geometry, `.dbf` for attributes, `.shx` for spatial index, `.prj` for CRS). Zipping them is standard practice for file transfer.
- **What an interviewer might ask**: *"What files must be present inside a Shapefile ZIP archive?"*
- **Concise answer**: *"A valid Shapefile requires at minimum `.shp`, `.shx`, and `.dbf` files. The `.prj` file is essential for CRS definition. We extract them safely into a temporary directory to parse with GeoPandas."*

---

### 6. How CRS Detection Works
- **What the code does**: Inspects `gdf.crs`. If `gdf.crs is None`, it raises `MissingCRSException` and fails processing with a clear status.
- **Why it does it**: Without a defined CRS, geometry coordinates are arbitrary numbers without spatial meaning. Silently assuming EPSG:4326 is dangerous and produces inaccurate spatial metrics.
- **What an interviewer might ask**: *"How do you handle files with missing CRS?"*
- **Concise answer**: *"We reject silent assumptions. If a file has no CRS, we fail the processing status with an explicit error message informing the client that measurements cannot be accurately computed without CRS metadata."*

---

### 7. Why EPSG:4326 Cannot Directly Be Used for Measurements
- **What the code does**: Identifies geographic CRS (`gdf.crs.is_geographic`) and transforms coordinates to a projected CRS before computing area/length.
- **Why it does it**: EPSG:4326 uses latitude and longitude in angular degrees on a 3D ellipsoid. Degree length varies by latitude. Measuring area in square degrees is physically meaningless and inaccurate.
- **What an interviewer might ask**: *"Why can't we compute `poly.area` directly on EPSG:4326 geometries?"*
- **Concise answer**: *"EPSG:4326 coordinates are angular degrees on a curved 3D Earth model. Calculating area directly in degrees yields square degrees, which vary with latitude. Reprojecting to a projected metric CRS like UTM projects coordinates onto a 2D Cartesian plane where 1 unit equals 1 meter."*

---

### 8. How Projected CRS Selection Works
- **What the code does**: Uses `gdf.estimate_utm_crs()` to select the local Universal Transverse Mercator (UTM) projection based on the dataset's geographic centroid/bounds.
- **Why it does it**: UTM divides the globe into 60 longitudinal zones, minimizing conformal scale distortion within each local 6-degree zone to under 0.04%.
- **What an interviewer might ask**: *"How does the service choose an appropriate projected CRS automatically?"*
- **Concise answer**: *"We use `estimate_utm_crs()` from GeoPandas/PyProj, which calculates the geographic bounding box of the dataset and selects the optimal local 6-degree UTM zone projection to minimize metric area and distance distortion."*

---

### 9. How Polygon Area is Calculated
- **What the code does**: Calls `geom.area` on reprojected `Polygon` geometries and returns value in `square_meters`.
- **Why it does it**: On a projected planar CRS (meters), geometry surface area represents true ground metric area.
- **What an interviewer might ask**: *"What units are returned for polygon measurements?"*
- **Concise answer**: *"Square meters (`square_meters`). Since geometries are reprojected into a metric projected CRS like UTM prior to calculation, Shapely's planar area calculation yields square meters directly."*

---

### 10. How LineString Length is Calculated
- **What the code does**: Calls `geom.length` on reprojected `LineString` geometries and returns value in `meters`.
- **Why it does it**: On projected planar coordinates, Euclidean segment lengths sum to total ground length in meters.
- **What an interviewer might ask**: *"How are 3D coordinates (with Z height) handled during linestring measurement?"*
- **Concise answer**: *"GeoPandas reprojection and Shapely length calculations operate on 2D projected coordinate planes, yielding horizontal ground distance in meters."*

---

### 11. How MultiPolygon / MultiLineString are Handled
- **What the code does**: Shapely `MultiPolygon.area` sums constituent polygon areas; `MultiLineString.length` sums constituent linestring lengths.
- **Why it does it**: Multipart geometries represent composite geographic features (such as island chains or divided roads) and require aggregate measurement.
- **What an interviewer might ask**: *"How do MultiPolygon and MultiLineString differ from single geometries?"*
- **Concise answer**: *"MultiPolygon and MultiLineString contain arrays of individual geometry parts. Shapely automatically aggregates their constituent planar area or length into a single total metric value."*

---

### 12. How Invalid Files are Handled
- **What the code does**: Rejects unsupported extensions (.txt), malformed ZIPs, missing shapefile components, corrupted KML, or empty files with HTTP 400 Bad Request.
- **Why it does it**: Prevents unhandled server exceptions, protects storage, and gives explicit feedback to API callers.
- **What an interviewer might ask**: *"What happens if a user uploads a corrupted KML file or empty zip?"*
- **Concise answer**: *"We validate extension, file size, ZIP structure, and OGR readability. Malformed uploads are caught during extraction/parsing and rejected with an HTTP 400 status code and detailed error message."*

---

### 13. How ZIP Path Traversal (Zip Slip) is Prevented
- **What the code does**: Resolves target paths for ZIP entries (`(target_dir / member.filename).resolve()`) and checks `member_path.startswith(target_dir)`.
- **Why it does it**: Malicious ZIP archives can contain filenames like `../../etc/passwd` that overwrite system files when blindly extracted.
- **What an interviewer might ask**: *"What is Zip Slip and how did you prevent it?"*
- **Concise answer**: *"Zip Slip is an arbitrary file overwrite vulnerability where a ZIP entry uses path traversal characters like `../`. We prevent it by resolving every zip member's absolute path and verifying it starts with the target extraction directory before extracting."*

---

### 14. Why the Processing Model (Synchronous) Was Chosen
- **What the code does**: Processes files synchronously within the HTTP request lifecycle while maintaining an explicit state machine (`UPLOADED` → `PROCESSING` → `COMPLETED`/`FAILED`).
- **Why it does it**: Keeps the architecture simple, testable, and explainable without adding unnecessary infrastructure complexity like Redis or Celery for standard small-to-medium files.
- **What an interviewer might ask**: *"Why execute file processing synchronously instead of asynchronously with Celery?"*
- **Concise answer**: *"For standard assessment datasets, synchronous execution eliminates unnecessary system dependencies like Redis or Celery, keeping the codebase clean and maintainable while maintaining explicit database status states."*

---

### 15. Database Design
- **What the code does**: Uses SQLAlchemy ORM with two models: `FileModel` (file metadata & status state machine) and `MeasurementModel` (feature-level spatial measurements).
- **Why it does it**: Avoids storing heavy raw geometry blobs in the relational DB. Stores indexed, structured numerical values and metadata.
- **What an interviewer might ask**: *"Why not store raw geometry data in PostGIS?"*
- **Concise answer**: *"Our service objective is feature measurement calculation rather than spatial indexing or GIS rendering. Storing lightweight numerical measurements and metadata in SQLite/Postgres keeps the database overhead minimal."*

---

### 16. API Design
- **What the code does**: Exposes 3 clean REST endpoints following standard HTTP methods and status codes (`POST 201`, `GET 200`, `400 Bad Request`, `404 Not Found`).
- **Why it does it**: Follows REST conventions and uses Pydantic schemas for response contracts.
- **What an interviewer might ask**: *"How are API error responses structured?"*
- **Concise answer**: *"All error responses follow FastAPI's standard `{ "detail": "error message" }` JSON schema with standard HTTP status codes (400 for validation errors, 404 for missing resources)."*

---

### 17. Testing Strategy
- **What the code does**: Automated test suite (`pytest`) with isolated in-memory SQLite database fixtures (`StaticPool`).
- **Why it does it**: Tests actual business logic (CRS transformation accuracy, measurement math, security validation) rather than just checking HTTP status codes.
- **What an interviewer might ask**: *"How do you test database operations in isolation?"*
- **Concise answer**: *"We use a pytest fixture with an in-memory SQLite database (`sqlite:///:memory:`) and SQLAlchemy's `StaticPool` so tests run in complete isolation in milliseconds."*

---

### 18. Potential Scalability Problems
- **What the code does**: Current design holds GeoDataFrames in RAM during processing.
- **Why it might scale poorly**: Uploading a 2 GB Shapefile could cause out-of-memory (OOM) errors if processed synchronously on a single web worker.
- **What an interviewer might ask**: *"What is the main bottleneck in your current architecture?"*
- **Concise answer**: *"In-memory GeoDataFrame loading and synchronous processing. Large files (>500MB) can cause high RAM usage and block FastAPI event loop workers."*

---

### 19. Modifications for Very Large Files
- **What the code does / What to change**:
  1. Use streaming chunked file uploads to S3/GCS object storage.
  2. Offload processing to background workers (FastAPI `BackgroundTasks`, Celery, or AWS Batch).
  3. Use iterative GDAL/Fiona streaming (`fiona.open()` feature iterator) instead of loading full GeoDataFrames into memory.
- **What an interviewer might ask**: *"How would you process a 5 GB geospatial file?"*
- **Concise answer**: *"I would stream the upload directly to S3, queue a background worker task using Celery, and process features iteratively using `fiona.open()` streaming rather than loading the whole file into RAM at once."*

---

### 20. Changes for Production Deployment
- **What to change for production**:
  - Replace SQLite with PostgreSQL / RDS.
  - Deploy with Gunicorn / Uvicorn workers behind an Nginx reverse proxy or AWS ALB.
  - Offload file storage to AWS S3 / Google Cloud Storage.
  - Add API key or JWT authentication middleware.
  - Add Prometheus metrics and OpenTelemetry logging.
- **What an interviewer might ask**: *"What would you add before deploying this service to production?"*
- **Concise answer**: *"I would switch to PostgreSQL, offload raw file uploads to AWS S3, introduce JWT authentication, set up worker process monitoring with Gunicorn/Prometheus, and run background tasks via Celery."*
