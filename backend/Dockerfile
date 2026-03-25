FROM python:3.12-slim

# Node.js 설치 (Claude Code CLI + GitHub MCP에 필요)
RUN apt-get update && apt-get install -y curl git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Claude Code CLI 설치
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# claude-agent-sdk 설치 후 FastAPI 호환 버전 복구
RUN pip install --no-cache-dir "starlette>=0.37.2,<0.39.0" "fastapi==0.115.0"

COPY . .

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
