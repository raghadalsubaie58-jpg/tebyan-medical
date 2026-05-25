FROM python:3.11-slim

WORKDIR /app

# System dependencies for OpenCV / EasyOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first (avoids pulling 2 GB of CUDA packages)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so first request is instant
# Model is cached in /app/model_cache (bind-mount a volume in prod for persistence)
ENV HF_HOME=/app/model_cache
RUN python -c "\
from langchain_huggingface import HuggingFaceEmbeddings; \
HuggingFaceEmbeddings(model_name='intfloat/multilingual-e5-large'); \
print('Model cached ✓')"

COPY . .

ENV PORT=8000

EXPOSE 8000

CMD ["python", "run.py"]
