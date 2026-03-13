# Stage 1: Frontend build
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and core modules
COPY backend/ ./backend/
COPY *.py ./
COPY template/ ./template/

# Copy built frontend into backend/static
COPY --from=frontend /app/backend/static ./backend/static/

# Create data directories
RUN mkdir -p data rag_storage

ENV HOST=0.0.0.0 PORT=8741 PYTHONUNBUFFERED=1
EXPOSE 8741

CMD ["python", "-m", "backend.main"]
