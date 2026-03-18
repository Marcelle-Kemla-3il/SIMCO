FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=10

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Pin versions known to work together (CPU-only)
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --timeout 300 --retries 10 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    numpy==1.26.4 \
    opencv-python-headless==4.8.1.78 \
    deepface==0.0.93 \
    tensorflow-cpu==2.15.1 \
    pillow==10.3.0

COPY app_cv ./app_cv

EXPOSE 8090

CMD ["python", "-m", "uvicorn", "app_cv.main:app", "--host", "0.0.0.0", "--port", "8090"]
