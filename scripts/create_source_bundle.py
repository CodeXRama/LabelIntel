"""Create a clean source-and-sample ZIP without local caches or credentials."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "dist" / "LabelIntel_Source_Data.zip"
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    "dist", "build", ".vite",
}
EXCLUDED_FILES = {"labelintel.db"}


def include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    # This image was an ad hoc user-provided working file, not a canonical
    # project fixture. Keep the submission data set limited to data/samples.
    if parts == ("burbon.jpg",):
        return False
    if any(part in EXCLUDED_DIRS for part in parts):
        return False
    if path.name in EXCLUDED_FILES or path.suffix.lower() in {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3"}:
        return False
    if parts[0] == "data":
        if len(parts) > 1 and parts[1] == "uploads":
            return False
        if len(parts) > 1 and parts[1] == "processed":
            return len(parts) >= 3 and parts[2] == "ocr_evaluation" and path.suffix.lower() == ".json"
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return False
    return path.is_file()


def main() -> None:
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in ROOT.rglob("*") if include(path) and path != ARCHIVE)
    with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED, compresslevel=7) as archive:
        for path in files:
            archive.write(path, Path("LabelIntel") / path.relative_to(ROOT))
    print(f"Created {ARCHIVE} with {len(files)} files ({ARCHIVE.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
