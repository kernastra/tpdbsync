# TPDB Poster Sync Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for SMB/CIFS
RUN apt-get update && \
    apt-get install -y cifs-utils smbclient fuse && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create intake folder (for volume mount)
RUN mkdir -p /app/intake

# Entrypoint
CMD ["python", "main.py"]
