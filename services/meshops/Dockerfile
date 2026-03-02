FROM python:3.12-slim

WORKDIR /app

COPY services/meshops/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/meshops/meshops/ ./meshops/

CMD ["python", "-m", "meshops.worker"]
