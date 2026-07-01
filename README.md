# VisionIQ

VisionIQ is a modular Streamlit application for extracting structured multiple-choice content from uploaded document images.

VisionIQ is currently under active development. The codebase is organized around
a clean, maintainable application structure:

- `app.py` keeps the Streamlit entrypoint minimal.
- `src/config.py` centralizes application constants and paths.
- `src/auth.py` contains authentication state and account actions.
- `src/database.py` owns SQLite persistence.
- `src/encryption.py` protects saved API keys.
- `src/components.py` contains reusable Streamlit UI components and styling.
- `src/ui.py` coordinates page flow.
- `src/file_utils.py` manages temporary files for uploads and exports.
- `src/usage_store.py` records local daily API usage.
- `src/groq_usage.py` tracks session-level request and token usage.
- `src/groq_service.py` sends prepared images to the extraction model.

## Development Status

The current implementation includes:

- User sign-in and account creation
- SQLite-backed account storage
- Encrypted API key storage
- Authenticated workspace shell
- Image upload staging interface
- Session and daily usage dashboard models
- Groq extraction service wrapper

The extraction pipeline is planned as dedicated modules for image preparation,
image processing, request orchestration, and PDF export.

## Run Locally

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

To save API keys securely, configure `FERNET_KEY` in `.streamlit/secrets.toml` or as an environment variable.
