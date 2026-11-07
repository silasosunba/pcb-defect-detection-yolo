FROM node:24-bookworm-slim AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ARG INSTALL_INFERENCE=false
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN if [ "$INSTALL_INFERENCE" = "true" ]; then uv sync --locked --no-dev --extra inference --python 3.12; else uv sync --locked --no-dev --python 3.12; fi
COPY backend/ ./backend/
COPY --from=ui /ui/dist/ ./frontend/dist/
RUN useradd --uid 10001 --create-home inspector && mkdir -p /app/data /app/models && chown -R inspector:inspector /app/data /app/models
USER inspector
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
