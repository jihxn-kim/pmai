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

# 패키지 호환성 수정:
# 1. claude-agent-sdk가 최신 mcp를 요구하므로 업그레이드
# 2. starlette/fastapi 호환 버전 복구
RUN pip install --no-cache-dir --upgrade mcp && \
    pip install --no-cache-dir "starlette>=0.37.2,<0.39.0" "fastapi==0.115.0"

COPY . .

# non-root 사용자 생성 (Claude Code CLI가 root에서 bypassPermissions 차단)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
