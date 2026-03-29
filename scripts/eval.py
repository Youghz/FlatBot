#!/usr/bin/env python3
"""Evaluate extraction accuracy against all labeled fixtures.

Loads local fixtures + optionally GCS fixtures, runs the extraction
logic on each, and prints an accuracy report per field.

Usage:
    uv run python scripts/eval.py              # local fixtures only
    uv run python scripts/eval.py --sync       # sync GCS first, then eval
    uv run python scripts/eval.py --verbose    # show each mismatch
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_labeling import _extract  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "labeling"
SAMPLES_FILE = FIXTURES_DIR / "samples.json"


def load_samples() -> list[dict]:
    with open(SAMPLES_FILE) as f:
        return json.load(f)


def evaluate(samples: list[dict], verbose: bool = False) -> dict:
    fields = {
        "furnished": {"correct": 0, "total": 0, "mismatches": []},
        "parking": {"correct": 0, "total": 0, "mismatches": []},
        "bedrooms": {"correct": 0, "total": 0, "mismatches": []},
        "move_in_date": {"correct": 0, "total": 0, "mismatches": []},
        "surface_sqft": {"correct": 0, "total": 0, "mismatches": []},
    }

    for sample in samples:
        fid = sample["fixture_id"]
        html_path = FIXTURES_DIR / f"{fid}.html"
        if not html_path.exists():
            continue

        try:
            data = _extract(fid)
        except Exception as e:
            if verbose:
                print(f"  SKIP {fid}: extraction failed: {e}")
            continue

        # Furnished
        label_f = sample.get("label_furnished")
        if label_f is not None:
            detected_f = data.get("furnished") if "furnished" in data else None
            fields["furnished"]["total"] += 1
            if label_f == "semi":
                ok = detected_f in (True, "semi")
            else:
                ok = detected_f == label_f
            if ok:
                fields["furnished"]["correct"] += 1
            else:
                fields["furnished"]["mismatches"].append((fid, label_f, detected_f))

        # Parking
        label_p = sample.get("label_parking")
        if label_p is not None:
            detected_p = data.get("parking") if "parking" in data else None
            fields["parking"]["total"] += 1
            if detected_p == label_p:
                fields["parking"]["correct"] += 1
            else:
                fields["parking"]["mismatches"].append((fid, label_p, detected_p))

        # Bedrooms
        label_b = sample.get("label_bedrooms")
        if label_b is not None:
            detected_b = data.get("bedrooms", 0)
            fields["bedrooms"]["total"] += 1
            if detected_b == label_b:
                fields["bedrooms"]["correct"] += 1
            else:
                fields["bedrooms"]["mismatches"].append((fid, label_b, detected_b))

        # Move-in date
        label_m = sample.get("label_move_in_date")
        if label_m:
            from flat_research.parsing import extract_move_in_date

            detected_m = extract_move_in_date(data["text"])
            fields["move_in_date"]["total"] += 1
            if detected_m == label_m:
                fields["move_in_date"]["correct"] += 1
            else:
                fields["move_in_date"]["mismatches"].append((fid, label_m, detected_m))

        # Surface
        label_s = sample.get("label_surface_sqft", 0)
        if label_s:
            from flat_research.parsing import extract_surface_sqft

            detected_s = extract_surface_sqft(data["text"])
            fields["surface_sqft"]["total"] += 1
            if detected_s == label_s:
                fields["surface_sqft"]["correct"] += 1
            else:
                fields["surface_sqft"]["mismatches"].append((fid, label_s, detected_s))

    return fields


def print_report(fields: dict, verbose: bool = False):
    total_correct = 0
    total_all = 0

    print("\n" + "=" * 60)
    print("EXTRACTION ACCURACY REPORT")
    print("=" * 60)

    for name, stats in fields.items():
        t = stats["total"]
        c = stats["correct"]
        total_correct += c
        total_all += t
        pct = f"{c / t * 100:.0f}%" if t else "N/A"
        bar = "#" * int(c / t * 20) + "." * (20 - int(c / t * 20)) if t else "." * 20
        status = "PASS" if c == t and t > 0 else "FAIL" if t > 0 else "SKIP"
        print(f"  {name:15s}  [{bar}]  {c:>2d}/{t:<2d}  {pct:>4s}  {status}")

        if verbose and stats["mismatches"]:
            for fid, expected, got in stats["mismatches"]:
                print(f"    {fid:14s}  expected={expected!s:>8s}  got={got!s:>8s}")

    print("-" * 60)
    pct_total = f"{total_correct / total_all * 100:.0f}%" if total_all else "N/A"
    print(f"  {'TOTAL':15s}                        {total_correct:>2d}/{total_all:<2d}  {pct_total:>4s}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate extraction accuracy")
    parser.add_argument("--sync", action="store_true", help="Sync GCS fixtures before eval")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show each mismatch")
    args = parser.parse_args()

    if args.sync:
        print("Syncing GCS fixtures...")
        from scripts.sync_fixtures import sync

        sync()

    samples = load_samples()
    # Filter to samples with HTML files
    valid = [s for s in samples if (FIXTURES_DIR / f"{s['fixture_id']}.html").exists()]
    print(f"Evaluating {len(valid)} labeled fixtures ({len(samples)} in samples.json)")

    fields = evaluate(valid, args.verbose)
    print_report(fields, args.verbose)


if __name__ == "__main__":
    main()
