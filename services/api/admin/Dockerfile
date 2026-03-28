FROM python:3.13-slim

WORKDIR /app

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

RUN pip install --no-cache-dir fastapi uvicorn python-multipart pyjwt passlib[bcrypt]

COPY services/api/admin/src ./src

EXPOSE 5002

CMD ["python", "-m", "src"]
