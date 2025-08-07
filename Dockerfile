# Multi-stage Dockerfile for both Lambda and local development
ARG TARGET=local

# Base stage for Lambda
FROM public.ecr.aws/lambda/python:3.11 AS lambda-base
COPY pyproject.toml README.md ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ${LAMBDA_TASK_ROOT}
COPY chat_api/ ${LAMBDA_TASK_ROOT}/chat_api/
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}"
# Note: Lambda handler would need to be implemented in chat_api for serverless
CMD ["chat_api.lambda_handler.handler"]

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