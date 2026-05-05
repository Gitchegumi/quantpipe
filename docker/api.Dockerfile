FROM python:3.12-slim

# Install system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.4

# Set workdir
WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock poetry.toml ./

# Install project dependencies (no-root = skip local package install)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# Copy source code + API
COPY src/ ./src/
COPY quantpipe_api/ ./quantpipe_api/

# Set PYTHONPATH so `import src.backtest...` works
ENV PYTHONPATH=/app/src
ENV QUANTPIPE_RESULTS_DIR=/app/results

EXPOSE 8000

# Run FastAPI app (module path from repo root)
CMD ["python", "-m", "uvicorn", "quantpipe_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
