FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/services/orders/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r saati && useradd -r -g saati saati
COPY --from=builder /install /usr/local
COPY backend/shared /app/shared
COPY backend/services/orders/app.py /app/app.py

USER saati
ENV PORT=8084 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8084
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8084/api/health')" || exit 1
CMD ["gunicorn", "-b", "0.0.0.0:8084", "-w", "2", "--threads", "4", "--graceful-timeout", "20", "app:app"]