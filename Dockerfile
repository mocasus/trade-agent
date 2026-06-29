FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e ".[all]"
COPY trade_agent/ ./trade_agent/
COPY config.example.yaml ./config.yaml
RUN mkdir -p /root/.trade-agent
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "trade_agent", "--config", "config.yaml"]
