FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# System deps kept minimal; add build-essential only if a wheel needs compiling.
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

# Hugging Face Spaces sends traffic to $PORT (defaults to 7860). Vercel/other
# hosts can override PORT. Shell form so ${PORT} expands at runtime.
EXPOSE 7860
CMD uvicorn career_assistant.api.app:app --host 0.0.0.0 --port ${PORT:-7860}
