from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://pmai:pmai@localhost:5432/pmai"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    frontend_url: str = "http://localhost:3000"

    # AI Engine
    anthropic_api_key: str = ""
    ai_repo_base_path: str = "/tmp/pmai/repos"
    ai_model: str = "claude-opus-4-6"
    ai_max_turns: int = 20

    # Slack
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
