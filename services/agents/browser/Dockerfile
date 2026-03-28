FROM python:3.13-slim

WORKDIR /app

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

COPY services/agents/browser/src ./src
COPY services/agents/browser/prompts ./prompts

EXPOSE 9004

CMD ["python", "-m", "src"]
