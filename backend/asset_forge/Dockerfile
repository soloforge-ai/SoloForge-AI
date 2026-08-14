FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the lightweight u2netp model during image build so the first
# production request does not have to download a model from Render at runtime.
# libgomp1 is required by onnxruntime on the slim Debian image.
RUN python -c "from rembg import new_session; new_session('u2netp')"

COPY main.py ./

EXPOSE 10000

# Render injects PORT at runtime. Fall back to its documented default (10000).
# Use exec so uvicorn becomes PID 1 and Render can observe the web process.
CMD ["sh", "-c", "exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --log-level info"]
