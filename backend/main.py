"""
LabelIntel — FastAPI Application
Endpoints for uploading, inspecting, and retrieving packaged commodity compliance reports.
"""

import csv
import io
import json
import hashlib
import threading
import time
from pathlib import Path
from typing import List, Optional
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models import InspectionModel
from backend.service import inspection_record_to_response, process_inspection

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_progress_lock = threading.Lock()
_pipeline_lock = threading.Lock()
_inspection_progress: dict[str, dict] = {}


def _set_inspection_progress(request_id: Optional[str], stage: str) -> None:
    if not request_id:
        return
    now = time.time()
    with _progress_lock:
        expired = [key for key, state in _inspection_progress.items() if now - state["updated_at"] > 900]
        for key in expired:
            _inspection_progress.pop(key, None)
        if len(_inspection_progress) >= 256 and request_id not in _inspection_progress:
            oldest = min(_inspection_progress, key=lambda key: _inspection_progress[key]["updated_at"])
            _inspection_progress.pop(oldest, None)
        _inspection_progress[request_id] = {"stage": stage, "updated_at": now}


def _run_inspection(progress_id: Optional[str], **kwargs):
    """Serialize model access while keeping the ASGI event loop responsive."""
    _set_inspection_progress(progress_id, "queued")
    with _pipeline_lock:
        try:
            return process_inspection(
                **kwargs,
                progress_callback=lambda stage: _set_inspection_progress(progress_id, stage),
            )
        except Exception:
            _set_inspection_progress(progress_id, "failed")
            raise

# Initialize database tables on startup
init_db()

app = FastAPI(
    title="LabelIntel API",
    description="AI-Assisted Packaged Commodity Inspection System",
    version="1.0.0",
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "LabelIntel Inspection API",
        "version": "1.0.0",
    }


@app.get("/api/samples")
def list_sample_images():
    """Discovers pre-existing packaging photographs in data/samples/ for quick demo."""
    samples_dir = Path("data/samples")
    if not samples_dir.exists():
        return []

    samples = []
    for p in sorted(samples_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
            rel = p.relative_to(samples_dir)
            category = rel.parts[0] if len(rel.parts) > 1 else "other"
            samples.append({
                "filename": p.name,
                "relative_path": str(rel).replace("\\", "/"),
                "category": category,
                "size_bytes": p.stat().st_size,
            })
    return samples


@app.get("/api/samples/image")
def get_sample_image(sample_path: str = Query(..., description="Relative image path inside data/samples")):
    """Serves a bundled sample photo for the inspection picker."""
    samples_dir = Path("data/samples").resolve()
    target = (samples_dir / sample_path).resolve()
    if not target.is_relative_to(samples_dir) or not target.is_file():
        raise HTTPException(status_code=404, detail="Sample image not found")
    if target.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".avif"}:
        raise HTTPException(status_code=404, detail="Unsupported sample image")
    return FileResponse(target)


@app.get("/api/inspection-progress/{request_id}")
def get_inspection_progress(request_id: str):
    """Returns the current stage for an in-flight inspection request."""
    with _progress_lock:
        state = _inspection_progress.get(request_id)
    if not state:
        return {"request_id": request_id, "stage": "waiting"}
    return {"request_id": request_id, "stage": state["stage"]}


@app.post("/api/inspections/upload")
async def upload_and_inspect(
    file: UploadFile = File(...),
    category: Optional[str] = Query(None, description="Packaging category hint (food, beverages, cosmetics, household)"),
    progress_id: Optional[str] = Header(None, alias="X-Inspection-Progress-ID"),
):
    """Uploads an image file and runs the end-to-end LabelIntel inspection pipeline."""
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            _set_inspection_progress(progress_id, "failed")
            raise HTTPException(status_code=413, detail="Image exceeds the 25 MB upload limit.")
        result = await run_in_threadpool(
            _run_inspection,
            progress_id=progress_id,
            file_bytes=content,
            filename=file.filename or "upload.jpg",
            category_hint=category,
        )
        if result.get("status") == "FAILED":
            _set_inspection_progress(progress_id, "failed")
            raise HTTPException(status_code=400, detail=result)
        _set_inspection_progress(progress_id, "complete")
        return result
    except HTTPException:
        _set_inspection_progress(progress_id, "failed")
        raise
    except Exception as e:
        _set_inspection_progress(progress_id, "failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/inspections/demo")
def run_demo_sample(
    sample_path: str = Query(..., description="Relative path of sample inside data/samples (e.g. food/food_001.jpg)"),
    refresh: bool = Query(False, description="Force a fresh OCR run instead of reusing a completed result"),
    progress_id: Optional[str] = Query(None, description="Optional client request id for progress polling"),
):
    """Runs the inspection pipeline on a pre-existing sample photograph."""
    samples_dir = Path("data/samples").resolve()
    target = (samples_dir / sample_path).resolve()
    if not target.is_relative_to(samples_dir) or not target.exists() or not target.is_file():
        _set_inspection_progress(progress_id, "failed")
        raise HTTPException(status_code=404, detail=f"Sample file not found: {sample_path}")

    category = target.parent.name
    _set_inspection_progress(progress_id, "checking_cache")
    if not refresh:
        sample_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        db = next(get_db())
        try:
            cached = (
                db.query(InspectionModel)
                .filter(
                    InspectionModel.file_hash == sample_hash,
                    InspectionModel.status == "COMPLETED",
                )
                .order_by(InspectionModel.created_at.desc())
                .first()
            )
            if cached and Path(cached.image_path).exists() and cached.annotated_path and Path(cached.annotated_path).exists():
                _set_inspection_progress(progress_id, "complete")
                return inspection_record_to_response(cached, reused_existing=True)
        finally:
            db.close()

    content = target.read_bytes()
    result = _run_inspection(
        progress_id=progress_id,
        file_bytes=content,
        filename=target.name,
        category_hint=category,
        force_refresh=refresh,
        sample_relative_path=target.relative_to(samples_dir).as_posix(),
    )
    if result.get("status") == "FAILED":
        _set_inspection_progress(progress_id, "failed")
        raise HTTPException(status_code=400, detail=result)
    _set_inspection_progress(progress_id, "complete")
    return result


@app.get("/api/inspections")
def list_inspections(db: Session = Depends(get_db)):
    """Lists recent inspection history."""
    records = db.query(InspectionModel).order_by(InspectionModel.created_at.desc()).limit(50).all()
    results = []
    for r in records:
        comp_data = json.loads(r.compliance_json) if r.compliance_json else {}
        results.append({
            "id": r.id,
            "filename": r.filename,
            "category": r.category,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "width": r.width,
            "height": r.height,
            "overall_compliance": comp_data.get("overall_status", "UNKNOWN"),
            "image_url": f"/api/inspections/{r.id}/image",
            "annotated_url": f"/api/inspections/{r.id}/annotated",
        })
    return results


@app.get("/api/inspection-analytics")
def get_inspection_analytics(db: Session = Depends(get_db)):
    """Summarizes stored inspection outcomes and rule checks for the dashboard."""
    records = (
        db.query(InspectionModel)
        .filter(InspectionModel.status == "COMPLETED")
        .order_by(InspectionModel.created_at.desc())
        .limit(200)
        .all()
    )
    overall = {"compliant": 0, "flagged_for_review": 0, "non_compliant": 0, "other": 0}
    rules: dict[str, dict] = {}
    for record in records:
        try:
            report = json.loads(record.compliance_json) if record.compliance_json else {}
        except (json.JSONDecodeError, TypeError):
            report = {}
        status = str(report.get("overall_status", "other")).lower().replace("-", "_").replace(" ", "_")
        overall[status if status in overall else "other"] += 1
        for assessment in report.get("assessments", []):
            rule = assessment.get("rule") or {}
            rule_id = str(rule.get("rule_id") or assessment.get("assessment_id") or rule.get("title") or "unknown")
            entry = rules.setdefault(rule_id, {
                "rule_id": rule_id,
                "title": str(rule.get("title") or "Unspecified check"),
                "rule_reference": str(rule.get("rule_reference") or ""),
                "applicable_count": 0,
                "pass_count": 0,
                "review_count": 0,
                "fail_count": 0,
            })
            assessment_status = str(assessment.get("status", "")).lower().replace("-", "_").replace(" ", "_")
            if assessment_status == "not_applicable":
                continue
            entry["applicable_count"] += 1
            if assessment_status == "compliant":
                entry["pass_count"] += 1
            elif assessment_status == "non_compliant":
                entry["fail_count"] += 1
            elif assessment_status == "flagged_for_review":
                entry["review_count"] += 1

    rule_rows = sorted(
        rules.values(),
        key=lambda entry: (entry["fail_count"] + entry["review_count"], entry["applicable_count"], entry["title"]),
        reverse=True,
    )
    return {
        "records_analyzed": len(records),
        "overall_counts": overall,
        "rule_counts": rule_rows[:8],
    }


def _safe_csv_value(value) -> str:
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@app.get("/api/inspections/export.csv")
def export_inspection_findings(db: Session = Depends(get_db)):
    """Downloads actual saved rule assessments as a spreadsheet-friendly CSV."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "Inspection ID", "Filename", "Checked at", "Category", "Check", "Rule",
        "Result", "Findings", "Review notes", "Evidence declaration ID",
    ])
    records = (
        db.query(InspectionModel)
        .filter(InspectionModel.status == "COMPLETED")
        .order_by(InspectionModel.created_at.desc())
        .all()
    )
    for record in records:
        try:
            report = json.loads(record.compliance_json) if record.compliance_json else {}
        except (json.JSONDecodeError, TypeError):
            report = {}
        for assessment in report.get("assessments", []):
            rule = assessment.get("rule") or {}
            writer.writerow(_safe_csv_value(value) for value in (
                record.id,
                record.filename,
                record.created_at.isoformat() if record.created_at else "",
                record.category,
                rule.get("title"),
                rule.get("rule_reference"),
                assessment.get("status"),
                " | ".join(assessment.get("findings") or []),
                " | ".join(assessment.get("cautions_and_recommendations") or []),
                assessment.get("evidence_declaration_id"),
            ))
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=labelintel-findings.csv"},
    )


@app.get("/api/inspections/{inspection_id}")
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    """Retrieves full details, bounding polygons, and compliance assessments for an inspection."""
    r = db.query(InspectionModel).filter(InspectionModel.id == inspection_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Inspection not found")
    response = inspection_record_to_response(r, reused_existing=True)
    response["created_at"] = r.created_at.isoformat() if r.created_at else None
    return response


@app.get("/api/inspections/{inspection_id}/image")
def get_inspection_image(inspection_id: str, db: Session = Depends(get_db)):
    """Serves the raw source image."""
    r = db.query(InspectionModel).filter(InspectionModel.id == inspection_id).first()
    if not r or not Path(r.image_path).exists():
        raise HTTPException(status_code=404, detail="Source image file not found")
    return FileResponse(r.image_path)


@app.get("/api/inspections/{inspection_id}/annotated")
def get_inspection_annotated(inspection_id: str, db: Session = Depends(get_db)):
    """Serves the annotated visual overlay image."""
    r = db.query(InspectionModel).filter(InspectionModel.id == inspection_id).first()
    if not r or not r.annotated_path or not Path(r.annotated_path).exists():
        raise HTTPException(status_code=404, detail="Annotated image file not found")
    return FileResponse(r.annotated_path)


# The container build places the Vite bundle here so one public URL serves both
# the browser UI and API. Local development continues to use Vite's /api proxy.
FRONTEND_DIST = Path("frontend/dist").resolve()
if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{frontend_path:path}", include_in_schema=False)
    def serve_frontend(frontend_path: str):
        if frontend_path == "api" or frontend_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        requested = (FRONTEND_DIST / frontend_path).resolve()
        if requested.is_relative_to(FRONTEND_DIST) and requested.is_file():
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")
