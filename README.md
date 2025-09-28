## Hygieia - Local, Private Medical AI

Hygieia is a lightweight, offline-first medical guidance assistant designed to bring high‑quality, PhD‑level medical knowledge to remote and private environments. It combines vision‑enabled multimodal LLMs with local fact‑checking and document import capabilities so that individuals and caregivers can access advanced medical guidance without sending sensitive data to the cloud.

This repository contains the desktop GUI, local AI orchestration code, simple web-scraping fact‑checks, and helpers for importing document and image evidence.

---

## Core idea

Give people a fast, empathetic, scientific medical assistant that runs locally on their machine (using Ollama), accepts text and images, can ingest documents, and - when useful - checks facts from reputable web resources. (Duodecim)

---

## Key features

- Local AI processing via Ollama for privacy (no remote model inference by default).
- Multimodal support: attach or drag & drop images (wound photos, skin rashes, scans) and get context‑aware responses.
- Document import: PDF, DOCX, PPTX content extraction via `anyFileRead.py`.
- Autonomous fact‑checking: the assistant can initiate or be asked to run a targeted web search (simple scraping) to cite sources.
- Friendly GUI built with PyQt6 (`GUI.py`) with keyboard shortcuts and a clean chat bubble UI.

---

## What Hygieia is - and is not

- Hygieia is a medical guidance and triage _assistant_ - it helps explain symptoms, suggests likely differential diagnoses, lists common next steps, and suggests questions to ask a clinician.
- It is explicitly NOT a replacement for a licensed medical professional. It should not be used as the sole basis for clinical decisions in emergencies.
- The assistant aims to be conservative: when uncertain it will say so and suggest escalation (e.g., seek in‑person care, emergency services).

---

## Quick start (Windows)

Prerequisites

- Python 3.10+ (or your system Python)
- Ollama installed and running locally with your chosen multimodal model (this project expects a model referenced as `llava_context` in code).
- Git (optional) and a terminal (cmd.exe)

Install and run

1. Create and activate a virtual environment (recommended):

```bat
python -m venv venv
venv\Scripts\activate
```

2. Install Python dependencies:

```bat
pip install -r requirements.txt
```

3. Make sure Ollama is installed and you have the local model available.

4. Start the app from the repository folder:

```bat
python Hygieia-AI.py
```

Tip: `Hygieia.bat` exists as a convenience launcher but it references a path/name - check it if it doesn't run on your machine.

---

## How to use the GUI (high level)

- Type your question into the input field and press Enter or click Send.
- Drag & drop or click "Attach Image" to upload images. Hygieia will encode the image and include it in the prompt for local model reasoning.
- Click "Import File" to parse PDFs, DOCX, and PPTX (via `anyFileRead.py`) and include the content in the conversation.
- Use `/search <query>` at the start of a message to run the built‑in fact‑check scraper (the assistant can also auto‑invoke searches). The current scraper targets `terveyskirjasto.fi` - update `WebSearch.py` to add other trusted sources.

Keyboard shortcuts

- Enter: send message
- Ctrl+L: clear conversation
- Ctrl+Up / Ctrl+Down: navigate recent messages

---

## Privacy & security

- All model inference is designed to run locally through Ollama. That protects sensitive information from leaving your device when the model calls are local.
- Web searches and scraping (used for fact‑checking) fetch content from the internet; those requests are external and will communicate with third‑party sites. If you need full offline operation, avoid `/search` and run Ollama + local models disconnected from the network.
- Images and imported document text are processed locally by the model; however, any use of networked search will expose query text and the data you included in search calls to the remote websites.

Security suggestions

- Prefer models you trust and run the Ollama daemon on a secure machine.
- Review and pin which remote sources the scraper uses.
- Avoid submitting identifiable patient data unless you have proper consent and an appropriate local security posture.

---

## Implementation notes (for maintainers)

- Entrypoint: `Hygieia-AI.py` - orchestrates the GUI and AI worker.
- GUI: `GUI.py` - PyQt6 chat UI, drag & drop for images, file import dialog, progress bar and history navigation.
- Document parsing: `anyFileRead.py` - reads PDF (PyPDF2), DOCX (python-docx), PPTX (python-pptx).
- Fact‑checking: `WebSearch.py` - uses `hrequests` + `beautifulsoup4` to query a site and extract paragraphs. This is intentionally minimal and should be improved for production (rate limiting, caching, trusted sources, and parsed citations).
- Local model calls: via the `ollama` Python package (see `Hygieia-AI.py`). The code uses `ollama.chat(..., stream=True)` to stream responses into the UI.

Model & prompt

- The code expects a local model named `llava_context` and defines a `SYSTEM_PROMPT` tuned for concise, empathetic medical responses. Change these to suit different models or moderation needs.

---

## Limitations & safety considerations

- Not exhaustive: the assistant summarizes and compresses context (to control token budgets). This may omit nuance - keep full clinical context when making decisions.
- Web scraping is brittle: remote site layout changes break parsers. Prefer APIs or curated, versioned medical databases for robust citation.
- Liability: this code is a research / helper tool. Do not rely on it for emergency diagnosis or as a sole decision support system.

Suggested improvements

- Add a configurable list of trusted sources and prefer structured APIs (PubMed, WHO, CDC, national libraries).
- Add input sanitization and a consent flow before uploading images or documents.
- Add content logging with user opt‑in to help improve model prompts and citation quality (locally stored only).

---

## Troubleshooting

- If the GUI starts but the assistant never responds:
  - Ensure Ollama is running and the `llava_context` model is available.
  - Check console logs for exceptions coming from the `ollama` calls.
- If file import fails for PDFs/DOCX/PPTX: ensure `PyPDF2`, `python-docx`, and `python-pptx` are installed (see `requirements.txt`).
- If the built‑in `Hygieia.bat` doesn't launch, open it and check the path and file name - the repository's main script is `Hygieia-AI.py` (note: the bat refers to `Hygieia_AI.py` in some environments; correct that if necessary).

---

## Contributing

Contributions are welcome. Please:

1. Open an issue describing your idea or bug.
2. Send a PR on the `main` branch with small, focused commits.

Areas that need help

- Improve fact‑checking and source handling.
- Add unit tests for file readers and web scrapers.
- Add automated model tests to verify prompts and streaming behavior.

---

## License & credits

This project is provided as‑is for research and humanitarian uses. Add a license file if you wish to apply a specific license (MIT, Apache‑2.0, etc.).

Thanks to the authors and maintainers of Ollama, PyQt6, BeautifulSoup, PyPDF2, python-docx and python-pptx for the building blocks.

---

If you'd like, I can also:

- add a CONTRIBUTING.md or LICENSE file,
- add a tiny test that verifies the document importers,
- or patch `Hygieia.bat` to point to the correct script name.

Enjoy - and remember: this is guidance, not a substitute for clinical care.
