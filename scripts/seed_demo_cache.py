"""
LabelIntel — Cache Seeder for Packaging Samples
Pre-populates the SQLite database for all demo packaging samples using evaluated OCR blocks
so that any sample demo or upload request resolves in < 100 milliseconds.
"""

import hashlib
import json
import time
from pathlib import Path

from backend.database import SessionLocal
from backend.models import InspectionModel
from backend.service import process_inspection


def seed_samples():
    samples_dir = Path("data/samples")
    db = SessionLocal()
    
    seeded_count = 0
    start_time = time.perf_counter()

    for p in sorted(samples_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue

        rel = p.relative_to(samples_dir)
        category = rel.parts[0] if len(rel.parts) > 1 else "other"
        content = p.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()

        # Check if already present with this hash
        existing = db.query(InspectionModel).filter(
            (InspectionModel.file_hash == file_hash) | (InspectionModel.filename == p.name)
        ).first()

        if existing and Path(existing.image_path).exists() and existing.annotated_path and Path(existing.annotated_path).exists():
            if not existing.file_hash:
                existing.file_hash = file_hash
                db.commit()
            print(f"[CACHE HIT] Already seeded: {rel} ({p.name})")
            continue

        print(f"[SEEDING] Processing {rel} ({p.name})...")
        t0 = time.perf_counter()
        result = process_inspection(
            file_bytes=content,
            filename=p.name,
            category_hint=category,
            force_refresh=False,
        )
        elapsed = time.perf_counter() - t0
        print(f"  -> Seeded {p.name} in {elapsed*1000:.1f} ms (Status: {result.get('status')})")
        seeded_count += 1

    db.close()
    total_sec = time.perf_counter() - start_time
    print(f"\nDone! Successfully verified/seeded demo samples in {total_sec:.2f} seconds.")


if __name__ == "__main__":
    seed_samples()
