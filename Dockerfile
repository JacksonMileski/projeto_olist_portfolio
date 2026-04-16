FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY notebooks/ ./notebooks/
COPY dados_tratados/ ./dados_tratados/

RUN mkdir -p graficos prints_sql prints_api prints_powerbi

EXPOSE 8000

CMD ["uvicorn", "notebooks.10_api_resultados:app", "--host", "0.0.0.0", "--port", "8000"]
