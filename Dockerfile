# Use glibc-based Node for reproducible Vite/Rollup builds on Render.
# Alpine's musl native optional dependency can fail during Rollup parsing.
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=optional
COPY frontend/ ./
RUN npm run build

FROM python:3.10-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-deploy.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-deploy.txt
# Download the default ONNX OCR models at image build time so the first hosted
# upload does not also pay the model-download delay.
RUN python -c "from rapidocr_onnxruntime import RapidOCR; RapidOCR()"
COPY backend/ ./backend/
COPY engines/ ./engines/
COPY data/samples/ ./data/samples/
# These verified snapshots make bundled demo samples open immediately without
# running CPU OCR on every Render request. Uploaded images still run live OCR.
COPY data/processed/ocr_evaluation/ ./data/processed/ocr_evaluation/
COPY --from=frontend-build /web/dist/ ./frontend/dist/
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
