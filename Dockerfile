# Backend Dockerfile for AI Skill Eval Platform
FROM python:3.12-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
# Copy source code
COPY . .

# Install uv and sync dependencies, fallback to pip if needed
RUN pip install --no-cache-dir uv && \
    (uv sync --frozen || pip install --no-cache-dir \
        fastapi \
        uvicorn \
        sqlalchemy \
        psycopg2-binary \
        python-dotenv \
        alembic \
        pydantic \
        pydantic-settings)

# Expose API port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
