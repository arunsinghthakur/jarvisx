FROM python:3.13-slim

WORKDIR /app

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

COPY services/agents/researcher/src ./src
COPY services/agents/researcher/prompts ./prompts

EXPOSE 9005

CMD ["python", "-m", "src"]
