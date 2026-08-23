FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY runtime.py ./
COPY backend ./backend
COPY data ./data

EXPOSE 10000

CMD ["sh", "-c", "exec python -m uvicorn runtime:app --host 0.0.0.0 --port ${PORT:-10000} --log-level info"]
