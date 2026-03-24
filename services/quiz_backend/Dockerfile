# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/services/quiz_backend

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "services.quiz_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
