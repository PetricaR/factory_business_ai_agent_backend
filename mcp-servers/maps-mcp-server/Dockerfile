FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY maps-mcp-server.py .

# Environment for Cloud Run
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# FastMCP automatically serves on the PORT env variable
CMD ["python", "maps-mcp-server.py"]
