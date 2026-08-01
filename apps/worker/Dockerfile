FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY apps/api/pyproject.toml ./
COPY apps/api/app ./app
COPY data/sources ./data/sources
RUN python -m pip install --no-cache-dir .

CMD ["python", "-m", "app.worker", "run"]
