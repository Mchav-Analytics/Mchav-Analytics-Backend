FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario y grupo sin privilegios de root (S6471)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -d /app appuser

# Copiar e instalar dependencias con caché optimizada
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia explícita de directorios de la aplicación para mitigar copias sensibles (S6470)
COPY app/ /app/app/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY README.md /app/README.md

# Asignar permisos y cambiar a usuario sin privilegios
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
