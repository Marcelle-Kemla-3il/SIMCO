FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential \
	libgl1 \
	libglib2.0-0 \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY REQUIREMENTS.txt .
RUN pip install --no-cache-dir -r REQUIREMENTS.txt

COPY . .

ENV PYTHONPATH=/app/src
ENV FACE_CLASSIFIER_PORT=8084
EXPOSE 8084

CMD ["python", "src/web/faces.py"]
