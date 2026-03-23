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
    gcc libffi-dev git && \
    rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (much smaller than CUDA version: ~200MB vs ~2GB)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --no-deps . && \
    pip install --no-cache-dir \
    "fastapi>=0.110.0" "uvicorn[standard]>=0.27.0" "python-multipart>=0.0.6" \
    "sqlalchemy>=2.0.25" "alembic>=1.13.0" \
    "pydantic>=2.5.0" "pydantic-settings>=2.1.0" \
    "requests>=2.31.0" "beautifulsoup4>=4.12.0" \
    "transformers>=4.36.0" "Pillow>=10.0.0" "safetensors>=0.4.0" \
    "structlog>=24.1.0"

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

# Download ML model at build time so it's baked into the image
RUN python -c " \
from transformers import ViTForImageClassification, ViTImageProcessor; \
name = 'dima806/10_ship_types_image_detection'; \
print('Downloading ViT ship classifier...'); \
p = ViTImageProcessor.from_pretrained(name); \
m = ViTForImageClassification.from_pretrained(name); \
p.save_pretrained('models/ship_classifier'); \
m.save_pretrained('models/ship_classifier'); \
print('Model saved.'); \
"

# Smoke test: verify torch + model load + inference works
RUN python -c " \
import torch; \
from transformers import ViTForImageClassification, ViTImageProcessor; \
from PIL import Image; \
print(f'PyTorch {torch.__version__} CPU'); \
proc = ViTImageProcessor.from_pretrained('models/ship_classifier'); \
model = ViTForImageClassification.from_pretrained('models/ship_classifier'); \
model.eval(); \
img = Image.new('RGB', (224, 224), (100, 150, 200)); \
inputs = proc(images=img, return_tensors='pt'); \
with torch.no_grad(): logits = model(**inputs).logits; \
pred = logits.argmax(-1).item(); \
print(f'Inference OK: {model.config.id2label[pred]} ({torch.softmax(logits, -1)[0, pred]:.2%})'); \
"

EXPOSE 3025

CMD ["sh", "-c", "python -m alembic upgrade head 2>/dev/null; python run.py"]
