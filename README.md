# VisionIQ

VisionIQ is a modular Streamlit workspace for extracting structured multiple-choice content from uploaded document images. The application is designed around a clean service-oriented layout, secure API-key handling, usage visibility, and a professional document-processing interface.

VisionIQ is currently under active development. The current build includes the application shell, authentication, API-key storage, usage dashboard models, and the Groq extraction service layer. Image preprocessing, extraction orchestration, result review, and PDF export are planned as the next pipeline modules.

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
- Temporary file utilities for future processing/export flow

## Interface

The UI uses a soft professional color palette with:

- muted blue-gray page background
- tinted workspace cards
- indigo/teal action colors
- compact account controls
- dashboard cards for usage visibility
- two-column upload and batch summary layout

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
    |-- file_utils.py
    |-- groq_service.py
    |-- groq_usage.py
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
- `src/ui.py` coordinates page flow, session state, API-key setup, upload staging, and dashboard rendering.
- `src/file_utils.py` manages temporary files for uploads and exports.
- `src/usage_store.py` records local daily API usage by hashed API key.
- `src/groq_usage.py` tracks session-level request and token usage and parses limit errors.
- `src/groq_service.py` sends prepared images to the Groq extraction model.

## Planned Pipeline

The next modules will connect the full extraction workflow:

- image compression and optimization
- screen/document crop preparation
- extraction runner for uploaded batches
- editable result review
- PDF export service
- persisted extraction history

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
- The current upload workflow stages files only; extraction orchestration will be connected in a later module.
- The usage dashboard is wired to the session tracker and daily usage store so it is ready for live extraction calls.
