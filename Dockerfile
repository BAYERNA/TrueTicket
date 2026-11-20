FROM node:24-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY data/seed.json data/seed.json
COPY data/evaluation/evaluation_set.json data/evaluation/evaluation_set.json
COPY scripts/serve.py scripts/serve.py
COPY --from=frontend /build/frontend/dist frontend/dist
ENV PORT=8000
EXPOSE 8000
CMD ["python", "scripts/serve.py"]
