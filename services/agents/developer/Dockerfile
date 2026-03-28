FROM python:3.13-slim

WORKDIR /app

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

COPY services/agents/developer/src ./src
COPY services/agents/developer/prompts ./prompts

EXPOSE 9000

CMD ["python", "-m", "src"]
