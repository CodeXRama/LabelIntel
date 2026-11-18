"""
LabelIntel — Automated Full Website & End-to-End Pipeline Test
Verifies:
1. Frontend dev server (Vite on http://127.0.0.1:5173) serves valid HTML, React entrypoint, and styles.
2. Backend API server (FastAPI on http://127.0.0.1:8000) responds to health check and samples list.
3. Full inspection workflow executed with a real packaging image (upload/demo).
4. Validation, quality assessment, OCR, NLP extraction, evidence fusion, and compliance output.
5. Rule provenance safety: source_status == 'unverified_reference' and absence of authoritative violation claims.
6. Retrieval of raw and annotated image visual assets.
7. Persistence into SQLite database and inspection history retrieval.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def test_website_e2e():
    frontend_url = "http://127.0.0.1:5173"
    backend_url = "http://127.0.0.1:8001"

    print("=" * 80)
    print("LabelIntel — Complete Website & End-to-End Integration Verification")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. Test Frontend Server (Vite)
    # -------------------------------------------------------------
    print("\n[Step 1/6] Verifying Frontend Dev Server...")
    try:
        with urllib.request.urlopen(f"{frontend_url}/", timeout=5) as resp:
            html = resp.read().decode("utf-8")
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            assert "<title>LabelIntel — AI Packaged Commodity Inspection</title>" in html, "Page title mismatch"
            assert 'id="root"' in html, "React root element missing"
            assert "/src/main.tsx" in html, "React entrypoint script missing"
            print("  ✓ Frontend HTML serves properly with correct title and React root.")
    except Exception as e:
        print(f"  ✗ Frontend server check failed: {e}")
        return False

    # -------------------------------------------------------------
    # 2. Test Backend Health & Samples Endpoints
    # -------------------------------------------------------------
    print("\n[Step 2/6] Verifying Backend API Server...")
    try:
        with urllib.request.urlopen(f"{backend_url}/api/health", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "healthy", f"Health status unexpected: {data}"
            print(f"  ✓ API Health: {data['app']} v{data['version']} (status: {data['status']})")

        with urllib.request.urlopen(f"{backend_url}/api/samples", timeout=5) as resp:
            samples = json.loads(resp.read().decode("utf-8"))
            assert len(samples) >= 7, f"Expected at least 7 packaging samples, got {len(samples)}"
            print(f"  ✓ Discovered {len(samples)} real commodity samples in data/samples/:")
            for s in samples[:4]:
                print(f"     - [{s['category']}] {s['filename']} ({(s['size_bytes']/1024):.1f} KB)")
    except Exception as e:
        print(f"  ✗ Backend API check failed: {e}")
        return False

    # -------------------------------------------------------------
    # 3. Execute End-to-End Inspection on Real Packaging Sample
    # -------------------------------------------------------------
    target_sample = "food/food_001.jpg"
    print(f"\n[Step 3/6] Running End-to-End Inspection on sample: '{target_sample}'...")
    print("  Triggering POST /api/inspections/demo ... (executing CV + OCR + NLP + Fusion + Compliance)")

    t0 = time.perf_counter()
    req = urllib.request.Request(
        f"{backend_url}/api/inspections/demo?sample_path={target_sample}",
        data=b"",
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            insp = json.loads(resp.read().decode("utf-8"))
            elapsed = time.perf_counter() - t0
            mode = "reused persisted result" if insp.get("reused_existing") else "fresh OCR run"
            print(f"  ✓ Pipeline completed in {elapsed:.1f} s ({mode}).")
    except Exception as e:
        print(f"  ✗ Pipeline execution failed: {e}")
        return False

    # -------------------------------------------------------------
    # 4. Verify Inspection Data Contracts & Quality Metrics
    # -------------------------------------------------------------
    print("\n[Step 4/6] Validating Processed Inspection Data Contracts...")
    inspection_id = insp["id"]
    print(f"  Inspection ID: {inspection_id}")
    print(f"  Status:        {insp['status']}")
    print(f"  Image Format:  {insp['metadata']['image_format']} ({insp['metadata']['width']}x{insp['metadata']['height']} px)")
    print(f"  Laplacian:     {insp['quality']['blur_laplacian_variance']:.1f} (Blurry: {insp['quality']['is_blurry']})")
    print(f"  Contrast:      {insp['quality']['contrast_std']:.1f}")
    print(f"  Highlight Sat: {(insp['quality']['clipping_high_pct']*100):.1f}%")
    print(f"  OCR Blocks:    {insp['ocr_summary']['total_blocks']} (Avg Conf: {(insp['ocr_summary']['average_confidence']*100):.1f}%)")
    print(f"  Fused Decls:   {len(insp['fused_declarations'])}")

    assert insp["status"] == "COMPLETED"
    assert insp["metadata"]["width"] == 1500
    assert insp["metadata"]["height"] == 1500
    assert len(insp["fused_declarations"]) > 0

    # -------------------------------------------------------------
    # 5. Verify Compliance Rules & Provenance Safety
    # -------------------------------------------------------------
    print("\n[Step 5/6] Verifying Statutory Compliance Assessment & Provenance Safety...")
    comp = insp["compliance_report"]
    print(f"  Overall Status:   {comp['overall_status']}")
    print(f"  Rules Evaluated:  {comp['total_rules_evaluated']}")
    print(f"  Compliant:        {comp['compliant_count']}")
    print(f"  Review Flagged:   {comp['flagged_count']}")
    print(f"  Non-Compliant:    {comp['non_compliant_count']}")

    assert "DISCLAIMER" in comp["legal_disclaimer"]

    for a in comp["assessments"]:
        rule = a["rule"]
        print(f"    [{a['status'].upper()}] {rule['title']} ({rule['rule_reference']})")
        print(f"         source_status: {rule.get('source_status')}")
        assert rule.get("source_status") == "unverified_reference", (
            f"Rule {rule['rule_id']} missing unverified_reference status!"
        )
        combined_text = " ".join(a["findings"] + a["cautions_and_recommendations"]).lower()
        assert "statutory violation" not in combined_text, "Found unverified 'statutory violation' claim!"
        assert "mandates" not in combined_text, "Found unverified 'mandates' claim!"

    print("  ✓ Provenance safety verified: All rules carry source_status='unverified_reference' and cautious phrasing.")

    # -------------------------------------------------------------
    # 6. Verify Image Artifact Endpoints & Database Persistence
    # -------------------------------------------------------------
    print("\n[Step 6/6] Verifying Image Artifact Endpoints & Persistence...")
    try:
        # Raw image endpoint
        with urllib.request.urlopen(f"{backend_url}{insp['image_url']}", timeout=10) as resp:
            img_bytes = resp.read()
            assert resp.status == 200
            assert len(img_bytes) > 1000
            print(f"  ✓ Raw source image served at {insp['image_url']} ({len(img_bytes)} bytes)")

        # Annotated image endpoint
        with urllib.request.urlopen(f"{backend_url}{insp['annotated_url']}", timeout=10) as resp:
            ann_bytes = resp.read()
            assert resp.status == 200
            assert len(ann_bytes) > 1000
            print(f"  ✓ CV Annotated visual overlay served at {insp['annotated_url']} ({len(ann_bytes)} bytes)")

        # History list endpoint
        with urllib.request.urlopen(f"{backend_url}/api/inspections", timeout=5) as resp:
            history = json.loads(resp.read().decode("utf-8"))
            matching = [h for h in history if h["id"] == inspection_id]
            assert len(matching) > 0, "Newly created inspection not found in history list!"
            print(f"  ✓ Database persistence verified: Inspection record persisted in SQLite and listed in history.")

    except Exception as e:
        print(f"  ✗ Artifact retrieval or history check failed: {e}")
        return False

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED: LabelIntel website and inspection pipeline are working as desired!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_website_e2e()
    sys.exit(0 if success else 1)
