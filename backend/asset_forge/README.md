# SoloForge Asset Forge API

This service turns one Asset Forge configuration into a processed sticker pack.

## Pipeline

1. Build a structured prompt.
2. Generate one consistent sticker sheet with Gemini image generation.
3. Split the sheet into an exact grid.
4. Remove the background from each cell with `rembg`.
5. Trim transparent margins.
6. Rename each PNG deterministically.
7. Package the PNG files into a ZIP archive.

## Environment variables

- `GEMINI_API_KEY` — required server-side secret.
- `GEMINI_IMAGE_MODEL` — optional; defaults to `gemini-3.1-flash-image`.
- `PORT` — optional; defaults to `8080` in the Docker image.

Never put `GEMINI_API_KEY` inside the Flutter application.

## Local run

```bash
cd backend/asset_forge
python -m venv .venv
# activate the environment
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
uvicorn main:app --reload --port 8080
```

Health check: `GET /health`

Generation endpoint: `POST /v1/asset-forge/generate`

The API currently returns the ZIP as base64 so the Flutter client can consume the result without exposing a storage service yet. A later production step should move the ZIP to object storage and return a short-lived download URL instead.
