from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Host/port as seen from wherever the DB is actually reached from - when
    # SSH_TUNNEL_HOST is set, that's from the SSH server's own perspective
    # (i.e. "localhost", since the DB runs on that same box), NOT from this
    # app's perspective. When no tunnel is configured, it's used directly.
    tasseer_db_host: str = "localhost"
    tasseer_db_port: int = 3306
    tasseer_db_name: str = "ksatntau_api"
    tasseer_db_user: str = ""
    tasseer_db_password: str = ""

    # SSH tunnel (only needed when this service runs somewhere that can't
    # reach the DB directly, e.g. Render - Namecheap shared hosting doesn't
    # expose MySQL remotely except via SSH port-forwarding, confirmed by
    # Namecheap support. Leave ssh_tunnel_host blank to skip the tunnel
    # entirely (e.g. when deployed directly on the same server as the DB).
    ssh_tunnel_host: str = ""
    ssh_tunnel_port: int = 21098
    ssh_tunnel_username: str = ""
    ssh_tunnel_private_key: str = ""  # PEM content, not a file path
    ssh_tunnel_private_key_passphrase: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    tasseer_api_base_url: str = "https://api.ksatasseerltdapi.com"

    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_support_phone_e164: str = ""

    support_env: str = "development"
    support_log_level: str = "INFO"


settings = Settings()
