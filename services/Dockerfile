# Dockerfile for FastAPI backend (static container)
# Base image: Python 3.12 slim
FROM python:3.12-slim AS base

# Set working directory inside the container
WORKDIR /app

# Install uv (modern Python package manager) globally
RUN pip install --no-cache-dir uv

# Copy only the API source folder (services/api) into the image
COPY api/ ./api/

# Install Python dependencies using uv
RUN uv pip install -r api/requirements.txt

# Expose the FastAPI default port
EXPOSE 8000

# Default command runs Uvicorn with hot‑reload for development
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

