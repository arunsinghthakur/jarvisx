FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY packages/core/ ./packages/core/

RUN pip install --no-cache-dir uv && \
    uv pip install --system -e ./packages/core && \
    uv pip install --system -e .

COPY services/agents/knowledge/ ./services/agents/knowledge/

VOLUME /app/workspaces

EXPOSE 9006

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "services.agents.knowledge.src"]
