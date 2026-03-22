# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim AS backend
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && pip install --no-cache-dir uvicorn

# Copy application code
COPY backend/ backend/
COPY ml_engine.py ./
COPY alembic.ini ./
COPY run.py ./
COPY schema.sql ./
COPY .env.example .env

# Copy built frontend
COPY --from=frontend /app/frontend-dist frontend-dist/

# Create data directories
RUN mkdir -p downloads uploads augmented models/ship_classifier data logs

EXPOSE 3025

# Run migrations then start server
CMD ["sh", "-c", "python -m alembic upgrade head 2>/dev/null; python run.py"]
