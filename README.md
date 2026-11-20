# LabelIntel

LabelIntel is a local-first web application for reviewing text printed on consumer product packages. It combines OCR, deterministic text extraction, image-coordinate evidence, and cautious rule-based screening. It is a student project and screening aid; it does not certify legal compliance.

## What works

- Upload a JPEG, PNG, WebP, or AVIF image (up to 25 MB) or choose a bundled package image.
- Run image validation and quality checks, OCR with RapidOCR/ONNX on CPU, and map detected text polygons back to the original image.
- Extract and normalize candidate declarations such as price, quantity, dates, manufacturer, contact, FSSAI, ingredients, and nutrition; link candidates to OCR blocks and coordinates.
- View the complete OCR text-region overlay and field evidence in the React interface.
- Save inspections, source images, overlays, and results in SQLite and retrieve recent history.
- Run heuristic compliance checks with source provenance and manual-review wording. A field not found on one photograph is not proof that the package is non-compliant.

The default runtime is RapidOCR/ONNX CPU, with PaddleOCR available as a compatibility fallback in the full local dependency set. There is no LLM, cloud OCR API, or GPU inference in the current pipeline. The sample OCR evaluation snapshots are used only for the matching bundled image selected through the demo endpoint; uploaded images always run live OCR. Cache reuse requires an exact image content hash.

## Run locally on Windows

Use Python 3.10 and Node.js 22. In PowerShell:

```powershell
cd D:\Projects\LabelIntel
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

In terminal 1, start the API:

```powershell
cd D:\Projects\LabelIntel
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

In terminal 2, start the website:

```powershell
cd D:\Projects\LabelIntel\frontend
npm ci
npm run dev
```

Open http://localhost:5173. The API health endpoint is http://127.0.0.1:8000/api/health and the interactive API reference is http://127.0.0.1:8000/docs. Keep both terminals running. The first fresh OCR run may take longer while models initialize; elapsed time depends on image detail and available CPU. Saved demo samples can reuse verified evaluation results. There is no hard 10-second guarantee for arbitrary uploads.

## Main API routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Service health |
| GET | `/api/samples` | Bundled demo image list |
| POST | `/api/inspections/upload?category=food` | Live OCR and inspection of an uploaded image |
| POST | `/api/inspections/demo?sample_path=food/food_001.jpg` | Inspect a bundled sample |
| GET | `/api/inspections` | Recent inspections |
| GET | `/api/inspections/{id}` | Full OCR, extraction, and screening evidence |

## Build and test

```powershell
cd D:\Projects\LabelIntel
.\.venv\Scripts\python.exe -m pytest tests -q
cd frontend
npm ci
npm run build
```

For an end-to-end API check, start the backend and run:

```powershell
cd D:\Projects\LabelIntel
.\.venv\Scripts\python.exe scripts\test_website_e2e.py
```

## Container deployment

A single-container build serves the React website and FastAPI endpoints from one origin. It uses a slim CPU dependency set and does not install the Paddle fallback:

```powershell
cd D:\Projects\LabelIntel
docker build -t labelintel .
docker run --rm -p 8000:8000 labelintel
```

Then open http://localhost:8000. Publish the image through a hosting service that supports Docker and set its service port to 8000. The container's SQLite database and uploaded files use the container filesystem; add a persistent volume before using it for durable history. Free hosting cold starts and CPU/memory limits can make OCR slower, so measure a real image on the chosen host before presenting a latency claim. This source tree has not been publicly deployed yet.

## Sample data

`data/samples/` contains genuine example packaging photographs. `data/processed/ocr_evaluation/` stores OCR outputs for seven images. `data/submission/ocr_region_samples.csv` is a reproducible 35-row sample of those actual OCR regions; rebuild it with:

```powershell
.\.venv\Scripts\python.exe scripts\export_submission_dataset.py
```

These are OCR observations, not ground-truth transcriptions. They do not establish OCR accuracy or compliance performance. See `data/submission/DATA_DICTIONARY.md` for the field definitions and limits.

## Project layout

- `backend/` — FastAPI routes, orchestration, and SQLite models
- `engines/cv_engine/` — image validation, quality analysis, preprocessing, OCR
- `engines/nlp_engine/` — declaration detection and normalization
- `engines/fusion/` — evidence-to-region linkage
- `engines/compliance_engine/` — deterministic heuristic checks and provenance
- `frontend/` — React, TypeScript, and Vite interface
- `tests/` — automated unit and contract tests
- `scripts/` — demo, integration check, and sample-data export
