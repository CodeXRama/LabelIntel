"""
LabelIntel — FastAPI Application
Endpoints for uploading, inspecting, and retrieving packaged commodity compliance reports.
"""

import json
from pathlib import Path
from typing import List, Optional
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models import InspectionModel
from backend.service import inspection_record_to_response, process_inspection

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
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            rel = p.relative_to(samples_dir)
            category = rel.parts[0] if len(rel.parts) > 1 else "other"
            samples.append({
                "filename": p.name,
                "relative_path": str(rel).replace("\\", "/"),
                "category": category,
                "size_bytes": p.stat().st_size,
            })
    return samples


@app.post("/api/inspections/upload")
async def upload_and_inspect(
    file: UploadFile = File(...),
    category: Optional[str] = Query(None, description="Packaging category hint (food, beverages, cosmetics, household)"),
):
    """Uploads an image file and runs the end-to-end LabelIntel inspection pipeline."""
    try:
        content = await file.read()
        result = process_inspection(
            file_bytes=content,
            filename=file.filename or "upload.jpg",
            category_hint=category,
        )
        if result.get("status") == "FAILED":
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/inspections/demo")
def run_demo_sample(
    sample_path: str = Query(..., description="Relative path of sample inside data/samples (e.g. food/food_001.jpg)"),
    refresh: bool = Query(False, description="Force a fresh OCR run instead of reusing a completed result"),
):
    """Runs the inspection pipeline on a pre-existing sample photograph."""
    samples_dir = Path("data/samples").resolve()
    target = (samples_dir / sample_path).resolve()
    if not target.is_relative_to(samples_dir) or not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Sample file not found: {sample_path}")

    category = target.parent.name
    if not refresh:
        db = next(get_db())
        try:
            cached = (
                db.query(InspectionModel)
                .filter(
                    InspectionModel.filename == target.name,
                    InspectionModel.category == category,
                    InspectionModel.status == "COMPLETED",
                )
                .order_by(InspectionModel.created_at.desc())
                .first()
            )
            if cached and Path(cached.image_path).exists() and cached.annotated_path and Path(cached.annotated_path).exists():
                return inspection_record_to_response(cached, reused_existing=True)
        finally:
            db.close()

    content = target.read_bytes()
    result = process_inspection(
        file_bytes=content,
        filename=target.name,
        category_hint=category,
        force_refresh=refresh,
    )
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


@app.get("/api/inspections/{inspection_id}")
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    """Retrieves full details, bounding polygons, and compliance assessments for an inspection."""
    r = db.query(InspectionModel).filter(InspectionModel.id == inspection_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Inspection not found")

    return {
        "id": r.id,
        "filename": r.filename,
        "category": r.category,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "metadata": {
            "width": r.width,
            "height": r.height,
            "file_size_bytes": r.file_size_bytes,
        },
        "quality": json.loads(r.quality_json) if r.quality_json else {},
        "ocr_blocks": json.loads(r.ocr_blocks_json) if r.ocr_blocks_json else [],
        "fused_declarations": json.loads(r.fused_declarations_json) if r.fused_declarations_json else [],
        "compliance_report": json.loads(r.compliance_json) if r.compliance_json else {},
        "image_url": f"/api/inspections/{r.id}/image",
        "annotated_url": f"/api/inspections/{r.id}/annotated",
    }


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
