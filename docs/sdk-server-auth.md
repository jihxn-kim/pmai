# Claude Agent SDK 서버 인증 가이드

## 배경

Claude Agent SDK는 내부적으로 Claude Code CLI를 subprocess로 실행한다.
CLI가 Anthropic API를 호출할 때 인증이 필요하며, 로컬과 서버에서 인증 방식이 다르다.

## 로컬 동작 원리

1. `claude login` → 브라우저 OAuth 인증
2. 토큰이 macOS Keychain (`Claude Code-credentials`)에 저장
3. CLI가 `claude.ai` 게이트웨이 경유로 API 호출
4. 구독(Max) 요금에 포함, 별도 API 비용 없음

## 서버에서의 문제

Anthropic이 서버/3rd party 환경에서 구독 인증을 정책적으로 차단함.

| 시도 | 결과 |
|------|------|
| `ANTHROPIC_API_KEY`에 setup-token 설정 | "Invalid API key" |
| `ANTHROPIC_AUTH_TOKEN`에 setup-token 설정 | "OAuth authentication is currently not supported" |
| Console API 키 발급 ($5 충전) | 동작 (토큰당 과금) |
| **로컬 Keychain credentials를 서버에 복사** | **동작 + 5x rate limit** |

## 현재 적용된 방식: Credentials 복사

### 구조

```
로컬 macOS Keychain
  └─ claudeAiOauth (accessToken + refreshToken)
       ↓ 추출
Railway 환경변수 CLAUDE_CREDENTIALS
       ↓ 컨테이너 시작 시
/home/appuser/.claude/.credentials.json
       ↓ CLI가 읽음
claude.ai 게이트웨이 경유 → 구독 인증으로 API 호출
```

### credentials 추출 방법

```bash
# macOS에서 실행
security find-generic-password -s "Claude Code-credentials" -w
```

출력 형태:
```json
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",
    "refreshToken": "sk-ant-ort01-...",
    "expiresAt": 1774518709557,
    "subscriptionType": "max",
    "rateLimitTier": "default_claude_max_5x"
  }
}
```

### Railway 환경변수 설정

```bash
railway variables set 'CLAUDE_CREDENTIALS=<위 JSON>'
```

### Dockerfile 처리

컨테이너 시작 시 환경변수에서 credentials 파일 생성:
```dockerfile
CMD ["sh", "-c", "if [ -n \"$CLAUDE_CREDENTIALS\" ]; then mkdir -p /home/appuser/.claude && echo \"$CLAUDE_CREDENTIALS\" > /home/appuser/.claude/.credentials.json && chmod 600 /home/appuser/.claude/.credentials.json; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## 폴백: Console API 키

credentials 방식이 실패할 경우 (refreshToken 갱신 안 됨 등):

1. [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key
2. Railway에 설정:
```bash
railway variables set ANTHROPIC_API_KEY="sk-ant-api03-..."
```

## 미확인 사항

- accessToken 만료 시 refreshToken 자동 갱신 여부
- 갱신 실패 시 → 로컬에서 credentials 재추출하여 업데이트하거나 Console API 키로 전환
