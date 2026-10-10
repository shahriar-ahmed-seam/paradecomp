# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build wheel

COPY src ./src
RUN pip install --no-cache-dir .

# Runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN groupadd -r paradecomp && useradd -r -g paradecomp -d /app -s /sbin/nologin paradecomp

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/paradecomp /usr/local/bin/paradecomp
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY src ./src

USER paradecomp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

ENTRYPOINT ["paradecomp"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
