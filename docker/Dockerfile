FROM python:3.11-slim

RUN useradd -m -u 1000 pulsetrader && \
    mkdir -p /app /app/data /app/logs /app/reports /app/runtime && \
    chown -R pulsetrader:pulsetrader /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=pulsetrader:pulsetrader . .

USER pulsetrader

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["python", "services/orchestrator/run.py"]
