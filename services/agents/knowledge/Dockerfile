FROM python:3.13-slim

WORKDIR /app

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

COPY services/agents/knowledge/src ./src
COPY services/agents/knowledge/prompts ./prompts

EXPOSE 9006

CMD ["python", "-m", "src"]
