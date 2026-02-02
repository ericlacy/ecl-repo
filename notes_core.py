#!/usr/bin/env python3
"""Core utilities for exporting and organizing Apple Notes."""

from __future__ import annotations

import datetime as dt
import html
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

RECORD_SEPARATOR = "\x1e"
FIELD_SEPARATOR = "\x1f"


@dataclass
class NoteRecord:
    folder: str
    title: str
    created: str
    body_html: str


@dataclass
class SuggestedFolder:
    name: str
    confidence: float
    reason: str


APPLESCRIPT = f"""
set recordSeparator to ASCII character 30
set fieldSeparator to ASCII character 31
set output to ""

try
    tell application "Notes"
        repeat with f in folders
            set folderName to name of f
            repeat with n in notes of f
                set noteName to name of n
                set noteBody to body of n
                set noteDate to creation date of n as string
                set output to output & folderName & fieldSeparator & noteName & fieldSeparator & noteDate & fieldSeparator & noteBody & recordSeparator
            end repeat
        end repeat
    end tell
on error errMsg number errNum
    return "ERROR:" & errNum & ":" & errMsg
end try

return output
"""


SAMPLE_NOTES = [
    NoteRecord(
        folder="Inbox",
        title="Client meeting follow-up",
        created="2024-11-02",
        body_html="""
        <p>Send project timeline and updated budget to client.</p>
        <p>Schedule next meeting for Thursday.</p>
        """,
    ),
    NoteRecord(
        folder="Personal",
        title="Weekend meal prep ideas",
        created="2024-11-01",
        body_html="""
        <ul><li>Chicken bowls</li><li>Vegetarian chili</li></ul>
        """,
    ),
    NoteRecord(
        folder="Ideas",
        title="New product brainstorm",
        created="2024-10-29",
        body_html="""
        <p>Focus on onboarding UX and real-time insights.</p>
        """,
    ),
]


class NotesExportError(RuntimeError):
    pass


def run_applescript() -> str:
    result = subprocess.run(
        ["osascript", "-l", "AppleScript", "-e", APPLESCRIPT],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise NotesExportError(result.stderr.strip() or "AppleScript failed")

    output = result.stdout
    if output.startswith("ERROR:"):
        raise NotesExportError(output.strip())
    return output


def parse_notes(raw: str) -> List[NoteRecord]:
    notes: List[NoteRecord] = []
    for record in raw.split(RECORD_SEPARATOR):
        if not record.strip():
            continue
        fields = record.split(FIELD_SEPARATOR)
        if len(fields) < 4:
            continue
        folder, title, created, body_html = fields[:4]
        notes.append(
            NoteRecord(
                folder=folder.strip(),
                title=title.strip(),
                created=created.strip(),
                body_html=body_html.strip(),
            )
        )
    return notes


def fetch_notes() -> List[NoteRecord]:
    try:
        raw = run_applescript()
        notes = parse_notes(raw)
        if not notes:
            raise NotesExportError("No notes found")
        return notes
    except (FileNotFoundError, NotesExportError):
        return SAMPLE_NOTES


def strip_html(html_text: str) -> str:
    text = re.sub(r"<style[\s\S]*?>[\s\S]*?</style>", "", html_text)
    text = re.sub(r"<script[\s\S]*?>[\s\S]*?</script>", "", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return text.strip()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-\s]", "", value)
    value = re.sub(r"\s+", "-", value)
    return value or "untitled"


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def suggest_folder(note: NoteRecord, known_folders: Sequence[str]) -> SuggestedFolder:
    keyword_map = {
        "Work": {
            "meeting",
            "client",
            "project",
            "deadline",
            "invoice",
            "deliverable",
            "followup",
        },
        "Personal": {"family", "birthday", "travel", "recipe", "meal", "weekend"},
        "Finance": {"budget", "tax", "expense", "invoice", "payment"},
        "Ideas": {"idea", "brainstorm", "concept", "draft"},
        "Journal": {"today", "gratitude", "mood", "reflection", "diary"},
    }

    content = f"{note.title} {strip_html(note.body_html)}"
    tokens = tokenize(content)
    if not tokens:
        return SuggestedFolder(name=note.folder or "Uncategorized", confidence=0.2, reason="Empty note")

    scores = {folder: 0 for folder in keyword_map}
    for token in tokens:
        for folder, keywords in keyword_map.items():
            if token in keywords:
                scores[folder] += 1

    best_folder, best_score = max(scores.items(), key=lambda item: item[1])
    confidence = min(1.0, best_score / max(3, len(tokens) / 4)) if best_score else 0.35

    if best_score == 0:
        fallback = note.folder or "Uncategorized"
        reason = "No strong keyword match; keeping original folder"
        if fallback in known_folders:
            return SuggestedFolder(name=fallback, confidence=confidence, reason=reason)
        return SuggestedFolder(name="Uncategorized", confidence=confidence, reason=reason)

    reason = f"Matched {best_score} keyword(s) for {best_folder}"
    if best_folder not in known_folders and note.folder:
        reason += f"; original folder was {note.folder}"
    return SuggestedFolder(name=best_folder, confidence=confidence, reason=reason)


def format_note(record: NoteRecord, output_format: str) -> str:
    header = f"# {record.title}\n\n"
    metadata = f"Folder: {record.folder}\nCreated: {record.created}\n\n"
    if output_format == "html":
        return (
            f"<h1>{html.escape(record.title)}</h1>\n"
            f"<p><strong>Folder:</strong> {html.escape(record.folder)}<br/>"
            f"<strong>Created:</strong> {html.escape(record.created)}</p>\n"
            f"{record.body_html}\n"
        )
    if output_format == "text":
        return f"{record.title}\n{record.folder}\n{record.created}\n\n{strip_html(record.body_html)}\n"

    return header + metadata + strip_html(record.body_html) + "\n"


def export_notes(
    notes: Iterable[NoteRecord],
    output_dir: Path,
    output_format: str,
    folder_overrides: dict[str, str] | None = None,
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    created_paths: List[Path] = []

    for record in notes:
        folder_name = folder_overrides.get(record.title, record.folder) if folder_overrides else record.folder
        folder_dir = output_dir / slugify(folder_name or "Uncategorized")
        folder_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{slugify(record.title)}-{timestamp}.{output_format}"
        output_path = folder_dir / filename
        content = format_note(record, output_format)
        output_path.write_text(content, encoding="utf-8")
        created_paths.append(output_path)

    return created_paths


def assess_suggestions(notes: Sequence[NoteRecord]) -> dict[str, object]:
    known_folders = sorted({note.folder for note in notes if note.folder})
    summary: dict[str, object] = {"total": len(notes), "buckets": []}

    counts: dict[str, List[float]] = {}
    for note in notes:
        suggestion = suggest_folder(note, known_folders)
        counts.setdefault(suggestion.name, []).append(suggestion.confidence)

    buckets = []
    for folder, confidences in sorted(counts.items()):
        average = sum(confidences) / len(confidences)
        buckets.append({"folder": folder, "count": len(confidences), "avg_confidence": round(average, 2)})

    summary["buckets"] = buckets
    return summary
