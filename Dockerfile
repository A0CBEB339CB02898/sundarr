FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY sundarr ./sundarr
COPY alembic.ini ./
COPY migrations ./migrations

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["uvicorn", "sundarr.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
