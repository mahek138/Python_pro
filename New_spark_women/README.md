# Spark Women Safety App

Portable Flask + PWA women safety app.

## 1. Copy Project To Another Laptop

Copy the full folder except optional local files like `.venv`.

## 2. Create Virtual Environment

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Environment Setup

1. Copy `.env.example` to `.env`
2. Fill values in `.env` (email, secret key, etc.)

## 5. Run App

```bash
python app.py
```

Open:

- `http://127.0.0.1:5000`

## 6. Quick Health Check

```bash
py -m py_compile app.py
```

## Notes For Portability

- Database is SQLite in `instance/app.db`. It auto-creates if missing.
- PWA features (install, service worker) work best on HTTPS (or localhost during development).
- For YouTube upload alerts, set `YOUTUBE_CHANNEL_ID` in `.env`.
