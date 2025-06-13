from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    postgres_user: str
    postgres_db: str
    postgres_password: str
    redis_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()