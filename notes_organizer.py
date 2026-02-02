#!/usr/bin/env python3
"""CLI for exporting and organizing Apple Notes content on macOS."""

from __future__ import annotations

import argparse
from pathlib import Path

from notes_core import (
    NotesExportError,
    export_notes,
    format_note,
    parse_notes,
    run_applescript,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export and organize Apple Notes content into folders.",
    )
    parser.add_argument(
        "--output",
        default="notes-export",
        help="Directory where notes will be exported.",
    )
    parser.add_argument(
        "--format",
        default="markdown",
        choices=["markdown", "text", "html"],
        help="Output file format.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a preview instead of writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        raw = run_applescript()
        notes = parse_notes(raw)
    except NotesExportError as exc:
        raise NotesExportError(f"Unable to read Notes: {exc}")

    if not notes:
        raise NotesExportError("No notes found. Ensure Notes access is permitted.")

    if args.dry_run:
        print(f"Found {len(notes)} notes. Sample output:\n")
        print(format_note(notes[0], args.format))
        return

    output_dir = Path(args.output).expanduser().resolve()
    created = export_notes(notes, output_dir, args.format)

    print(f"Exported {len(created)} notes to {output_dir}")


if __name__ == "__main__":
    main()
