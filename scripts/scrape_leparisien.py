#!/usr/bin/env python
"""Scrape Le Parisien / RCI Jeux mots fleches grids."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from urllib.error import HTTPError

from flechebench.data.leparisien import fetch_puzzle, latest_issues, save_puzzles, write_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", type=int, default=1, choices=[1, 2, 3, 4])
    parser.add_argument("--all-forces", action="store_true", help="Scrape forces 1, 2, 3 and 4.")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=Path("data/leparisien"))
    parser.add_argument("--redownload", action="store_true", help="Download grids even when JSON files already exist.")
    parser.add_argument("--skip-missing", action="store_true", help="Skip grids that return 404.")
    parser.add_argument(
        "--through-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Latest publication date to include, in YYYY-MM-DD format.",
    )
    return parser.parse_args()


def scrape_force(
    force: int,
    count: int,
    through_date: date,
    output_dir: Path,
    skip_missing: bool,
    redownload: bool,
) -> None:
    issues = latest_issues(force, count, through_date)
    force_output_dir = output_dir / f"force{force}"
    puzzles = []

    for issue in issues:
        puzzle_path = force_output_dir / f"mfleches_{issue.force}_{issue.number}.json"
        if puzzle_path.exists() and not redownload:
            print(f"skip existing force={issue.force} number={issue.number} date={issue.published_on}")
            continue

        print(f"fetch force={issue.force} number={issue.number} date={issue.published_on}")
        try:
            puzzles.append(fetch_puzzle(issue.force, issue.number, issue.published_on))
        except HTTPError as error:
            if skip_missing and error.code == 404:
                print(f"skip missing force={issue.force} number={issue.number}")
                continue
            raise

    if puzzles:
        save_puzzles(puzzles, force_output_dir)
    elif force_output_dir.exists():
        write_index(force_output_dir)
    print(f"saved {len(puzzles)} puzzles to {force_output_dir}")


def main() -> None:
    args = parse_args()
    forces = [1, 2, 3, 4] if args.all_forces else [args.force]
    for force in forces:
        scrape_force(force, args.count, args.through_date, args.output_dir, args.skip_missing, args.redownload)


if __name__ == "__main__":
    main()
