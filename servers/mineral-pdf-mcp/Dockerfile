FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install optional PDF parsing deps (uncomment to enable real PDF support)
# RUN pip install --no-cache-dir httpx PyMuPDF

COPY . .

EXPOSE 8002

CMD ["python", "server.py"]
