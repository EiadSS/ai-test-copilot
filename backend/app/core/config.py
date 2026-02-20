from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str
    redis_url: str

    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5.2"
    openai_embed_model: str = "text-embedding-3-small"

    embedding_dim: int = 1536
    chunk_size: int = 1200
    chunk_overlap: int = 200
    rag_top_k: int = 8

settings = Settings()
