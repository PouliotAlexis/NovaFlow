# NovaFlow Backend Dockerfile
FROM python:3.11-slim

# Configuration de l'environnement
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8000

WORKDIR /app

# Installation des dépendances système (nécessaires pour psycopg2, Playwright, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    # Dépendances système pour Playwright/Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation de Chromium pour Playwright (nécessaire pour SSO Moodle si utilisé en headless)
RUN playwright install chromium

# Copie du code source
COPY . .

# Exposition du port
EXPOSE 8000

# Lancement du serveur (Gunicorn avec workers Uvicorn pour la prod)
CMD gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT
