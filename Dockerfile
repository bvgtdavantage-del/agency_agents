FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY setup.py .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["bash"]
