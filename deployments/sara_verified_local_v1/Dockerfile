FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SARA_BIND_HOST=0.0.0.0 \
    SARA_PORT=9530 \
    SARA_DATA_DIR=/var/lib/sara

RUN useradd --create-home --uid 10001 sara
WORKDIR /app
COPY pyproject.toml README.md ./
COPY worldshepherd_sara ./worldshepherd_sara
RUN pip install --no-cache-dir .
RUN mkdir -p /var/lib/sara && chown -R sara:sara /var/lib/sara /app && chmod 0700 /var/lib/sara
USER sara
EXPOSE 9530
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9530/readyz', timeout=2)" || exit 1
CMD ["python", "-m", "worldshepherd_sara"]
