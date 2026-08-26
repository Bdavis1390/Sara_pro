FROM python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17

ARG SARA_BUILD_COMMIT=UNKNOWN
ARG SARA_RELEASE_ID=UNVERIFIED

LABEL org.opencontainers.image.title="Worldshepherd SARA Verified Local v1" \
      org.opencontainers.image.revision="${SARA_BUILD_COMMIT}" \
      org.opencontainers.image.version="${SARA_RELEASE_ID}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SARA_BIND_HOST=0.0.0.0 \
    SARA_PORT=9530 \
    SARA_DATA_DIR=/var/lib/sara \
    SARA_BUILD_COMMIT=${SARA_BUILD_COMMIT} \
    SARA_RELEASE_ID=${SARA_RELEASE_ID}

RUN useradd --create-home --uid 10001 sara
WORKDIR /app
COPY pyproject.toml README.md constraints-runtime.txt ./
COPY worldshepherd_sara ./worldshepherd_sara
RUN pip install --no-cache-dir --disable-pip-version-check -c constraints-runtime.txt .
RUN mkdir -p /var/lib/sara && chown -R sara:sara /var/lib/sara /app && chmod 0700 /var/lib/sara
USER sara
EXPOSE 9530
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9530/readyz', timeout=2)" || exit 1
CMD ["python", "-m", "worldshepherd_sara"]
