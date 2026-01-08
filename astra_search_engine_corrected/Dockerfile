FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     ASTRA_DB_PATH=/data/astra.db

WORKDIR /app

# system deps for lxml
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential libxml2-dev libxslt1-dev     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY astra /app/astra
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md

RUN mkdir -p /data

EXPOSE 8000

CMD ["python", "-m", "astra.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
