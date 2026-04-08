FROM python:3.11-slim

# Install Node.js + uv
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Install frontend dependencies
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN npm ci && npm ci --prefix frontend

# Install backend dependencies
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen

# Copy all source code
COPY . .

# Build frontend
RUN cd frontend && npm run build

# Create backend directories
RUN mkdir -p backend/uploads/simulations backend/uploads/projects backend/uploads/reports

# HF Spaces uses port 7860
ENV PORT=7860
EXPOSE 7860

# Start backend serving both API and static frontend
CMD ["bash", "-c", "cd backend && uv run python run_hf.py"]
