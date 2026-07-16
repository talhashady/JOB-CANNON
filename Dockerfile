FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system libraries for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install chromium binary for Playwright
RUN playwright install chromium

COPY . .
RUN pip install --no-cache-dir -e .

# Hugging Face Spaces sends traffic to $PORT (defaults to 7860). Vercel/other
# hosts can override PORT. Shell form so ${PORT} expands at runtime.
EXPOSE 7860
CMD uvicorn career_assistant.api.app:app --host 0.0.0.0 --port ${PORT:-7860}
