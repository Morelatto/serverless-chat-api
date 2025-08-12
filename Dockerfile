# Multi-stage Dockerfile for both Lambda and local development
ARG TARGET=local

# Base stage for Lambda
FROM public.ecr.aws/lambda/python:3.11 AS lambda-base
COPY pyproject.toml README.md ${LAMBDA_TASK_ROOT}/
# Install dependencies including mangum for Lambda adapter
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir mangum && \
    pip install --no-cache-dir ${LAMBDA_TASK_ROOT}
COPY chat_api/ ${LAMBDA_TASK_ROOT}/chat_api/

# Create the handler file inline - cleaner than complex CMD
RUN echo "from mangum import Mangum\nfrom chat_api.api import app\nhandler = Mangum(app, lifespan='off')" > ${LAMBDA_TASK_ROOT}/handler.py

ENV PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}"
CMD ["handler.handler"]

# Base stage for local development
FROM python:3.11-slim AS local-base
WORKDIR /app
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .
COPY chat_api ./chat_api
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app
USER appuser
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "chat_api"]

# Final stage selector
FROM ${TARGET}-base AS final
