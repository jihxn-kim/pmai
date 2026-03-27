FROM python:3.12-slim

# Node.js 설치 (Claude Code CLI + GitHub MCP에 필요)
RUN apt-get update && apt-get install -y curl git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Claude Code CLI + Playwright MCP 설치
RUN npm install -g @anthropic-ai/claude-code @playwright/mcp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 패키지 호환성 수정:
# 1. claude-agent-sdk가 최신 mcp를 요구하므로 업그레이드
# 2. starlette/fastapi 호환 버전 복구
RUN pip install --no-cache-dir --upgrade mcp && \
    pip install --no-cache-dir "starlette>=0.37.2,<0.39.0" "fastapi==0.115.0"

COPY . .

# Playwright 의존성 설치 (root에서)
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libwayland-client0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# non-root 사용자 생성 (Claude Code CLI가 root에서 bypassPermissions 차단)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Playwright 브라우저 설치 (appuser로 실행 — 홈 디렉토리에 설치됨)
RUN npx playwright install chromium

CMD ["sh", "-c", "if [ -n \"$CLAUDE_CREDENTIALS\" ]; then mkdir -p /home/appuser/.claude && echo \"$CLAUDE_CREDENTIALS\" > /home/appuser/.claude/.credentials.json && chmod 600 /home/appuser/.claude/.credentials.json; fi && python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
