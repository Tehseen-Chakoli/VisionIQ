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

## Development Status

The current implementation includes:

- User sign-in and account creation
- SQLite-backed account storage
- Encrypted API key storage
- Authenticated workspace shell
- Image upload staging interface

The extraction pipeline is planned as dedicated modules for image preparation,
model requests, usage tracking, and PDF export.

## Run Locally

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

To save API keys securely, configure `FERNET_KEY` in `.streamlit/secrets.toml` or as an environment variable.
