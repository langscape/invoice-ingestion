FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/

EXPOSE 8000

CMD ["uvicorn", "invoice_ingestion.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
