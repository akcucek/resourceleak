FROM python:3.12-slim
WORKDIR /app
COPY backend backend
COPY frontend frontend
ENV PORT=8080 RL_DB=/tmp/resourceleak.sqlite3
WORKDIR /app/backend
CMD ["python3", "-m", "resourceleak"]
