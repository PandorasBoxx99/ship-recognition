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

# Install system dependencies (incl. Playwright browser deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev git \
    # Playwright/Chromium dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (much smaller: ~200MB vs ~2GB)
RUN pip install --no-cache-dir \
    "torch>=2.0.0,<3.0.0" "torchvision>=0.15.0,<1.0.0" \
    --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install project as package
COPY pyproject.toml ./
COPY backend/ backend/
COPY ml_engine.py ./
RUN pip install --no-cache-dir -e ".[browser]"

# Install Playwright Chromium
RUN python -m playwright install chromium

# Copy remaining application code
COPY alembic.ini ./
COPY run.py ./
COPY .env.example .env

# Copy built frontend
COPY --from=frontend /app/frontend-dist frontend-dist/

# Create data directories
RUN mkdir -p downloads uploads augmented models/ship_classifier data logs

# Download ML model at build time
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

# Smoke test
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
