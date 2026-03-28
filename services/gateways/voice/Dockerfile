FROM python:3.13-slim

WORKDIR /app

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

RUN pip install --no-cache-dir starlette uvicorn asyncclick

COPY services/gateways/voice/src ./src

EXPOSE 9003

CMD ["python", "-m", "src"]
