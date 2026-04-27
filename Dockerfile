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
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "Some packages failed, installing core only..." && \
     pip install --no-cache-dir fastapi uvicorn[standard] websockets python-multipart PyJWT \
       google-genai openai anthropic python-docx python-pptx pypdf PyMuPDF pandas openpyxl \
       XlsxWriter python-dotenv requests beautifulsoup4 lxml Pillow httpx)

# Copy backend and core modules
COPY backend/ ./backend/
COPY dartwings/ ./dartwings/
COPY docx_markup/ ./docx_markup/
COPY vendor/ ./vendor/
COPY *.py ./
COPY template/ ./template/

# Copy built frontend into backend/static
COPY --from=frontend /app/backend/static ./backend/static/

# Create data directories
RUN mkdir -p data rag_storage

ENV HOST=0.0.0.0 PORT=8741 PYTHONUNBUFFERED=1
EXPOSE 8741

CMD ["python", "-m", "backend.main"]
