#!/usr/bin/env python3
"""Web UI for organizing Apple Notes on macOS."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from notes_core import assess_suggestions, export_notes, fetch_notes, suggest_folder

app = Flask(__name__)


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/notes")
def api_notes():
    notes = fetch_notes()
    known_folders = sorted({note.folder for note in notes if note.folder})

    payload = []
    for note in notes:
        suggestion = suggest_folder(note, known_folders)
        payload.append(
            {
                "title": note.title,
                "folder": note.folder,
                "created": note.created,
                "body_html": note.body_html,
                "suggested_folder": suggestion.name,
                "confidence": suggestion.confidence,
                "reason": suggestion.reason,
            }
        )

    return jsonify({"notes": payload, "folders": known_folders})


@app.get("/api/assess")
def api_assess():
    notes = fetch_notes()
    return jsonify(assess_suggestions(notes))


@app.post("/api/export")
def api_export():
    payload = request.get_json(force=True)
    output_dir = Path(payload.get("output_dir", "notes-export")).expanduser().resolve()
    output_format = payload.get("format", "markdown")
    overrides = payload.get("overrides", {})

    notes = fetch_notes()
    created = export_notes(notes, output_dir, output_format, overrides)

    return jsonify({"count": len(created), "output_dir": str(output_dir)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
