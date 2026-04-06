FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy source code
COPY . .

# Create uploads directory
RUN mkdir -p uploads/simulations uploads/projects uploads/reports

EXPOSE 5001

CMD ["uv", "run", "python", "run.py"]
