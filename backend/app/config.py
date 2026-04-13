from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Meta / WhatsApp
    meta_app_id: str = ""
    meta_app_secret: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_webhook_verify_token: str = "heyzenzai_webhook_secret"

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "https://api.heyzenzai.com/oauth/callback"

    # AI
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ai_provider: str = "gemini"  # "gemini" | "openai"

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # App
    app_env: str = "development"  # "development" | "production"
    owner_alert_phone: str = ""  # E.164 format e.g. +6591234567
    base_url: str = "https://api.heyzenzai.com"


settings = Settings()
