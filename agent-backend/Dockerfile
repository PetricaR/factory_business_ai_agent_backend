FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire app
COPY . .

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

# Run using python -m instead of uvicorn binary
# This avoids exec format errors on multi-arch builds
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]