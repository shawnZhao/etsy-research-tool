from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://etsy:etsy_dev@localhost:5432/etsy_research"
    database_url_sync: str = "postgresql://etsy:etsy_dev@localhost:5432/etsy_research"
    redis_url: str = "redis://localhost:6379/0"
    etsy_api_key: str = ""
    etsy_api_secret: str = ""
    etsy_api_base_url: str = "https://openapi.etsy.com/v3/"
    keyword_cache_ttl: int = 3600

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
