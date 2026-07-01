# VisionIQ

VisionIQ is a modular Streamlit workspace for extracting structured multiple-choice content from uploaded document images. The application is designed around a clean service-oriented layout, secure API-key handling, usage visibility, and a professional document-processing interface.

VisionIQ is currently under active development. The current build includes authentication, encrypted API-key storage, a usage dashboard, image preparation, Groq-powered extraction, editable result review, and PDF export.

## Current Features

- User sign-in and account creation
- SQLite-backed account and usage persistence
- Encrypted API-key storage with Fernet
- Professional Streamlit workspace UI
- Image upload staging interface
- Batch summary panel
- Usage dashboard for request and token limits
- Local daily API usage tracking
- Session-level usage tracker
- Groq extraction service wrapper
- Conservative document/screen crop preparation
- JPEG optimization before model requests
- Batch extraction orchestration
- Editable extraction review area
- Light and dark PDF export

## Interface

The UI uses a soft professional color palette with:

- muted blue-gray page background
- tinted workspace cards
- indigo/teal action colors
- compact account controls
- dashboard cards for usage visibility
- two-column upload and batch summary layout
- expandable result review sections
- compact export controls

## Project Structure

```text
VisionIQ/
|-- app.py
|-- requirements.txt
|-- README.md
|-- .streamlit/
|   `-- config.toml
`-- src/
    |-- auth.py
    |-- components.py
    |-- config.py
    |-- database.py
    |-- encryption.py
    |-- extraction_runner.py
    |-- file_utils.py
    |-- groq_service.py
    |-- groq_usage.py
    |-- image_compressor.py
    |-- image_processor.py
    |-- pdf_service.py
    |-- screen_cropper.py
    |-- ui.py
    `-- usage_store.py
```

## Module Overview

- `app.py` keeps the Streamlit entrypoint minimal.
- `src/config.py` centralizes application constants, model settings, limits, and paths.
- `src/auth.py` contains authentication state and account actions.
- `src/database.py` owns SQLite persistence for users, API keys, and token usage.
- `src/encryption.py` encrypts and decrypts saved API keys.
- `src/components.py` contains reusable Streamlit UI components and styling.
- `src/ui.py` coordinates page flow, session state, API-key setup, extraction actions, and dashboard rendering.
- `src/file_utils.py` manages temporary files for uploads and exports.
- `src/usage_store.py` records local daily API usage by hashed API key.
- `src/groq_usage.py` tracks session-level request and token usage and parses limit errors.
- `src/groq_service.py` sends prepared images to the Groq extraction model.
- `src/image_compressor.py` normalizes, resizes, and compresses images for model requests.
- `src/screen_cropper.py` detects and crops the main document/screen region when it is safe to do so.
- `src/image_processor.py` combines crop and compression steps for extraction-ready images.
- `src/extraction_runner.py` coordinates uploaded files, preparation, model calls, usage persistence, and batch results.
- `src/pdf_service.py` creates reviewed PDF exports from extraction results.

## Extraction Pipeline

The current extraction flow is intentionally modular:

1. Upload PNG or JPEG images.
2. Prepare each image with conservative crop detection and JPEG optimization.
3. Send the prepared image to the configured Groq Vision model.
4. Record successful and failed request usage locally.
5. Review and edit extracted text in the workspace.
6. Export reviewed successful results to PDF.

## Planned Improvements

- Persist named extraction jobs
- Add extraction history and re-export
- Add optional prompt profiles
- Add automated tests for image preparation and PDF export

## Run Locally

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Local Secrets

To save API keys securely, configure `FERNET_KEY` in `.streamlit/secrets.toml` or as an environment variable.

Generate a key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Create `.streamlit/secrets.toml`:

```toml
FERNET_KEY = "paste_generated_key_here"
```

## Notes

- Local databases and secrets are ignored by git.
- The usage dashboard is wired to the session tracker and daily usage store for live extraction calls.
- Review extracted text before using or sharing exported PDFs.
