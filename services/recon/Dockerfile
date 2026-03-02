FROM python:3.12-slim

WORKDIR /app

COPY services/recon/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/recon/recon/ ./recon/

CMD ["python", "-m", "recon.worker"]
