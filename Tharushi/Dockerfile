FROM python:3.12-slim

WORKDIR /app

# System dependencies for geopandas/rasterio
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 --retries 10 -r requirements.txt

# Copy application code
COPY . .

EXPOSE 5001

CMD ["python", "app.py"]
