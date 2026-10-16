FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/services/images/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r saati && useradd -r -g saati saati
COPY --from=builder /install /usr/local
COPY backend/shared /app/shared
COPY backend/services/images/app.py /app/app.py

USER saati
ENV PORT=8083 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8083
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8083/api/health')" || exit 1
CMD ["gunicorn", "-b", "0.0.0.0:8083", "-w", "2", "--threads", "4", "--graceful-timeout", "20", "app:app"]