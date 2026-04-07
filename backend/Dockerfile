FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app/backend

# Copy backend dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy backend source
COPY backend/ .

# Copy locales to expected location (3 levels up from app/utils/)
COPY locales/ /app/locales/

# Create uploads directory
RUN mkdir -p uploads/simulations uploads/projects uploads/reports

EXPOSE 5001

CMD ["uv", "run", "python", "run.py"]
