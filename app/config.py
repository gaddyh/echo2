import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    d360_api_key: str
    d360_api_base_url: str
    webhook_auth_mode: str
    webhook_bearer_token: str
    webhook_basic_user: str
    webhook_basic_pass: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("D360_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Missing D360_API_KEY. Copy example.env to .env and set it.")

        auth_mode = os.getenv("WEBHOOK_AUTH_MODE", "none").strip().lower()
        if auth_mode not in {"none", "bearer", "basic"}:
            raise RuntimeError("WEBHOOK_AUTH_MODE must be one of: none, bearer, basic")

        return cls(
            d360_api_key=api_key,
            d360_api_base_url=os.getenv("D360_API_BASE_URL", "https://waba-v2.360dialog.io").rstrip("/"),
            webhook_auth_mode=auth_mode,
            webhook_bearer_token=os.getenv("WEBHOOK_BEARER_TOKEN", "").strip(),
            webhook_basic_user=os.getenv("WEBHOOK_BASIC_USER", "").strip(),
            webhook_basic_pass=os.getenv("WEBHOOK_BASIC_PASS", "").strip(),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
