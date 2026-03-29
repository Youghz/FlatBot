#!/usr/bin/env python3
"""Download user-generated test fixtures from GCS bucket.

Merges GCS fixtures with the local repo fixtures in tests/fixtures/labeling/.
Run before pytest to include user corrections in regression tests.

Usage:
    python scripts/sync_fixtures.py
    # or: uv run python scripts/sync_fixtures.py
"""

import json
import os
import sys
from pathlib import Path

BUCKET_NAME = os.environ.get("FIXTURES_BUCKET", "flatbot-fixtures")
LOCAL_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "labeling"
LOCAL_SAMPLES = LOCAL_DIR / "samples.json"


def sync():
    try:
        from google.cloud import storage
    except ImportError:
        print("google-cloud-storage not installed, skipping GCS sync")
        return

    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
    except Exception as e:
        print(f"Could not connect to GCS bucket {BUCKET_NAME}: {e}")
        return

    # Download GCS samples.json
    gcs_samples_blob = bucket.blob("samples.json")
    if not gcs_samples_blob.exists():
        print("No GCS fixtures found (samples.json not in bucket)")
        return

    gcs_samples = json.loads(gcs_samples_blob.download_as_text())
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
            blob = bucket.blob(f"{fid}.{ext}")
            if blob.exists():
                dest = LOCAL_DIR / f"{fid}.{ext}"
                blob.download_to_filename(str(dest))

        local_samples.append(sample)
        local_ids.add(fid)
        new_count += 1

    if new_count:
        with open(LOCAL_SAMPLES, "w") as f:
            json.dump(local_samples, f, indent=2, ensure_ascii=False, default=str)
        print(f"Synced {new_count} new fixtures from GCS → {LOCAL_DIR}")
    else:
        print("No new fixtures to sync")


if __name__ == "__main__":
    sync()
    sys.exit(0)
