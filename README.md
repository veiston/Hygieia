# Hygieia – Local, Private Medical Assistant 👩‍⚕️🏥

Hygieia is an offline medical guidance assistant that delivers high-quality medical knowledge privately. It supports text, images, and document import, with optional fact-checking from trusted sources.

<img width="598" height="797" alt="Screenshot" src="https://github.com/user-attachments/assets/40dbadd0-959a-4e63-abfc-af9aaef8026f" />

---

## Features

- Local AI inference (privacy-first).
- Multimodal support: upload images (wounds, rashes, scans).
- Document import: PDF, DOCX, PPTX (`anyFileRead.py`).
- Optional fact-checking (`WebSearch.py`).
- PyQt6 GUI (`GUI.py`) with chat bubbles, drag & drop, and shortcuts.

---

## What it is – and isn’t

- **Assistant**: suggests diagnoses, next steps, and clinician questions.
- **Not a replacement** for licensed medical care.
- Conservative: flags uncertainty and suggests escalation.

---

## Quick Start (Windows)

Prerequisites:

- Python 3.10+
- Ollama installed with a local model (`llava_context`)
- Optional: Git and terminal

Install and run:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python Hygieia-AI.py
```
---

## Using the GUI

- Type questions → Enter / Send.
- Drag & drop images → included in reasoning.
- Import PDFs/DOCX/PPTX → adds content to conversation.
- `/search <query>` → run fact-checks (`terveyskirjasto.fi`).

Shortcuts:

- Enter: send
- Ctrl+L: clear conversation
- Ctrl+Up / Ctrl+Down: navigate messages

---

## Privacy & Security

- All AI inference is local.
- Web searches expose some bits of user prompt data; avoid `/search` for offline-only use.
- Use trusted models, review sources, and avoid identifiable patient data without consent.

---

## Maintainers

- `Hygieia-AI.py` – main orchestrator
- `GUI.py` – chat UI
- `anyFileRead.py` – document parsing
- `WebSearch.py` – minimal fact-checking
- Local model calls via `ollama.chat(..., stream=True)`

---

## Limitations

- Summarizes context; may omit nuance.
- Scraping is fragile; prefer structured APIs.
- Research / helper tool only; not emergency-ready.

---

## Contributing

1. Open an issue with your idea or bug.
2. PR to `main` with small commits.

Help wanted: fact-check improvements, unit tests, prompt verification.

---

## License

This project is GPL-3.0 licensed.

Credits to Ollama, PyQt6, BeautifulSoup, PyPDF2, python-docx, and python-pptx.
