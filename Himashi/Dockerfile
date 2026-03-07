FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and data
COPY api.py .
COPY train_model.py .
COPY risk_and_cluster.py .
COPY model/ ./model/

EXPOSE 8001

# Run the API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001"]
