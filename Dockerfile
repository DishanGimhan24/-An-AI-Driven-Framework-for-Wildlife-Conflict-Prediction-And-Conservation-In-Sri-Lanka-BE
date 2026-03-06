FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and data
COPY api.py .
COPY data_preparation.py .
COPY corridor_detection.py .
COPY model_training.py .
COPY run.py .
COPY uploads/ ./uploads/
COPY outputs/ ./outputs/
COPY data/ ./data/

EXPOSE 8000

# Run the API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
