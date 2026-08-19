FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/asset_forge/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/asset_forge/main.py ./main.py
COPY backend/pollinations_oauth.py ./pollinations_oauth.py
COPY backend/pollinations_oauth_router.py ./pollinations_oauth_router.py
COPY backend/asset_forge/characters ./characters

EXPOSE 10000

CMD ["sh", "-c", "exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --log-level info"]
