FROM python:3.13-slim

LABEL maintainer="CivGraph" \
      version="0.1.0" \
      description="Agent-based model of urban social dynamics"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py ./
COPY static/ static/

# Create saves directory
RUN mkdir -p saves

EXPOSE 8420

# Run with 0.0.0.0 binding inside container (container networking handles isolation)
CMD ["python", "-c", "import uvicorn; uvicorn.run('server:app', host='0.0.0.0', port=8420)"]
