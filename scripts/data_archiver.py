"""Monthly CSV archive migration script.

Moves last month's CSV/JSON files from data/ and its subdirectories into
data/archive/YYYY-MM/ on the 1st of each month.
"""

import argparse
import datetime
import shutil
from pathlib import Path

from config import ARCHIVE_DIR, DATA_DIR, DEEP_DATA_DIR, SECTOR_FLOW_DIR


def _last_month(today):
    """Return year and month for the calendar month preceding `today`."""
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def _fmt_ym(year, month):
    return f"{year}-{month:02d}"


def _move_files(src_dir, pattern, dest_dir, dry_run=False):
    """Move files matching `pattern` from src_dir into dest_dir.

    Returns a list of (src, dst) Path tuples for every file that was moved
    (or would be moved, when dry_run=True).
    """
    moved = []
    if not src_dir.exists():
        return moved
    for f in src_dir.glob(pattern):
        if not f.is_file():
            continue
        dst = dest_dir / f.name
        if not dry_run:
            shutil.move(str(f), str(dst))
        moved.append((f, dst))
    return moved


def archive_if_month_boundary(force_ym=None, dry_run=False):
    """Archive last month's data files if today is the 1st (or force_ym is set).

    Parameters
    ----------
    force_ym : str or None
        "YYYY-MM" to force archive a specific month (bypasses date check).
    dry_run : bool
        Report what would be moved without actually moving files.

    Returns
    -------
    list[tuple[Path, Path]]
        (source, destination) for every file moved (or that would be moved).
    """
    today = datetime.date.today()

    if force_ym:
        year_str, month_str = force_ym.split("-")
        year, month = int(year_str), int(month_str)
    else:
        if today.day != 1:
            print(f"Today is {today} — not the 1st of the month. Nothing to archive.")
            return []
        year, month = _last_month(today)

    ym_label = _fmt_ym(year, month)
    dest = ARCHIVE_DIR / ym_label
    dest.mkdir(parents=True, exist_ok=True)

    # Date-based patterns that match the target month
    date_prefixes = [f"{year}-{month:02d}", f"{year}{month:02d}"]
    csv_patterns = [f"*{p}*.csv" for p in date_prefixes]
    json_patterns = [f"*{p}*.json" for p in date_prefixes]

    results = []

    # 1. Top-level data/*.csv from last month
    for pat in csv_patterns:
        results.extend(_move_files(DATA_DIR, pat, dest, dry_run))

    # 2. data/sector_flow/*.csv from last month
    for pat in csv_patterns:
        results.extend(_move_files(SECTOR_FLOW_DIR, pat, dest, dry_run))

    # 3. data/deep/*.json from last month
    for pat in json_patterns:
        results.extend(_move_files(DEEP_DATA_DIR, pat, dest, dry_run))

    if dry_run:
        mode = "[DRY RUN] Would move"
    else:
        mode = "Moved"

    if results:
        print(f"\n{mode} {len(results)} file(s) to {dest}/:")
        for src, dst in results:
            print(f"  {src.name}")
    else:
        print(f"\n{mode} 0 files (no files matched for {ym_label}).")

    return [(src, dst) for src, dst in results]


def main():
    parser = argparse.ArgumentParser(
        description="Archive last month's data files to data/archive/YYYY-MM/."
    )
    parser.add_argument(
        "--force", metavar="YYYY-MM",
        help="Force archive a specific month (e.g. 2026-04)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be moved without actually moving."
    )
    args = parser.parse_args()
    archive_if_month_boundary(force_ym=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
