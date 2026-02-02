# Apple Notes Organizer

Apple Notes Organizer is a macOS app and CLI that exports your local Apple Notes into a structured folder tree. It uses AppleScript to pull notes from the Notes app, suggests folders based on note content, and writes them out as Markdown, text, or HTML so you can archive, search, or reorganize them locally.

## Features

- Export all notes from every Notes folder.
- Suggest folders based on content context.
- Assess suggested folders with confidence scoring.
- Organize exports into per-folder directories.
- Choose Markdown, plain text, or HTML output.
- Web UI and CLI workflows.

## Requirements

- macOS with the Notes app.
- Python 3.9+.
- `pip install -r requirements.txt` for the web UI.
- Permission for `osascript` to control Notes (you will be prompted the first time).

## Web app usage

```bash
pip install -r requirements.txt
python3 app.py
```

Open <http://localhost:5000> to review suggestions, assess folders, and export your notes.

## CLI usage

```bash
python3 notes_organizer.py --output ~/Documents/notes-export --format markdown
```

### Dry run

```bash
python3 notes_organizer.py --dry-run
```

### Output formats

- `markdown` (default)
- `text`
- `html`

## Notes and limitations

- Apple Notes bodies are stored as HTML; Markdown output is best-effort and strips HTML tags.
- Large notebooks may take a few seconds to export.
- The exporter uses your local Notes data only; it does not sync or modify notes.
- If Apple Notes access is unavailable, the web UI shows sample notes so you can preview the organizer.

## Troubleshooting

If you see an error like `ERROR:-1743`, open **System Settings → Privacy & Security → Automation** and allow `osascript` to control **Notes**.
