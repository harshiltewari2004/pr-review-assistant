FROM python:3.11-slim
WORKDIR /app

# CPU-only torch first. The default PyPI wheel bundles CUDA libraries this
# service never uses — same weights, same embeddings, roughly half the image.
# Installed separately because the +cpu wheels are Linux/Windows only, so the
# pin cannot live in requirements.txt without breaking macOS local installs.
RUN pip install --no-cache-dir torch==2.3.1 \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bind $PORT when the platform sets one (Cloud Run injects it), else 7860.
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
