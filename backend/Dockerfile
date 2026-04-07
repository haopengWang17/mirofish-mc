FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

RUN mkdir -p uploads/simulations uploads/projects uploads/reports

EXPOSE 5001

CMD ["uv", "run", "python", "run.py"]
