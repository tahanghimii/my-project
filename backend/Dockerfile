# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml requirments.txt ./
RUN pip wheel --no-deps --no-cache-dir --wheel-dir wheels -r requirments.txt

# Copy source code
COPY src src
RUN pip wheel --no-deps --no-cache-dir --wheel-dir wheels .

# Stage 2: Runner
FROM python:3.12-slim AS runner

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY src/mysite mysite

EXPOSE 8000
CMD ["uvicorn", "mysite.main:app", "--host", "0.0.0.0", "--port", "8000"]
