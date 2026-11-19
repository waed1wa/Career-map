# Один образ для трёх контейнеров: api, worker и beat (модульный монолит)
FROM python:3.12-slim

WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8000
# Команда по умолчанию — API. В docker-compose.yml для worker и beat она переопределена.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
