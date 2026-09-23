from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tasseer_db_host: str = "localhost"
    tasseer_db_port: int = 3306
    tasseer_db_name: str = "ksatntau_api"
    tasseer_db_user: str = ""
    tasseer_db_password: str = ""

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    tasseer_api_base_url: str = "https://api.ksatasseerltdapi.com"

    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_support_phone_e164: str = ""

    support_env: str = "development"
    support_log_level: str = "INFO"

    @property
    def db_url(self) -> str:
        return (
            f"mysql+pymysql://{self.tasseer_db_user}:{self.tasseer_db_password}"
            f"@{self.tasseer_db_host}:{self.tasseer_db_port}/{self.tasseer_db_name}?charset=utf8mb4"
        )


settings = Settings()
