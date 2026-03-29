#!/usr/bin/env python3
"""Download user-generated test fixtures from GCS bucket.

Merges GCS fixtures with the local repo fixtures in tests/fixtures/labeling/.
Run before pytest to include user corrections in regression tests.

Usage:
    uv run python scripts/sync_fixtures.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

BUCKET_NAME = "flatbot-fixtures"
BUCKET_URL = f"gs://{BUCKET_NAME}"
LOCAL_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "labeling"
LOCAL_SAMPLES = LOCAL_DIR / "samples.json"


def _gcloud_bin() -> str:
    return shutil.which("gcloud") or "gcloud"


def _gcs_download(blob_path: str, dest: Path) -> bool:
    """Download a file from GCS using gcloud CLI."""
    try:
        subprocess.run(
            [_gcloud_bin(), "storage", "cp", f"{BUCKET_URL}/{blob_path}", str(dest)],
            capture_output=True,
            check=True,
            timeout=30,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def sync():
    # Download GCS samples.json to temp
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    if not _gcs_download("samples.json", tmp_path):
        print("No GCS fixtures found (samples.json not in bucket or bucket inaccessible)")
        tmp_path.unlink(missing_ok=True)
        return

    try:
        gcs_samples = json.loads(tmp_path.read_text())
    except (json.JSONDecodeError, OSError):
        print("Failed to parse GCS samples.json")
        tmp_path.unlink(missing_ok=True)
        return
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"Found {len(gcs_samples)} fixtures in GCS bucket")

    # Load local samples
    if LOCAL_SAMPLES.exists():
        with open(LOCAL_SAMPLES) as f:
            local_samples = json.load(f)
    else:
        local_samples = []

    local_ids = {s["fixture_id"] for s in local_samples}
    new_count = 0

    for sample in gcs_samples:
        fid = sample["fixture_id"]
        if fid in local_ids:
            continue

        # Download HTML and TXT files
        for ext in ("html", "txt"):
            dest = LOCAL_DIR / f"{fid}.{ext}"
            _gcs_download(f"{fid}.{ext}", dest)

        local_samples.append(sample)
        local_ids.add(fid)
        new_count += 1

    if new_count:
        with open(LOCAL_SAMPLES, "w") as f:
            json.dump(local_samples, f, indent=2, ensure_ascii=False, default=str)
        print(f"Synced {new_count} new fixtures from GCS -> {LOCAL_DIR}")
    else:
        print("No new fixtures to sync")


if __name__ == "__main__":
    sync()
    sys.exit(0)
