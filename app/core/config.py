import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: str
    CHROMA_DB_PATH: str = "./chroma_db"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # We can default to Llama-3.3-70b-versatile or llama3-70b-8192
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
# In tests or development we might not have GROQ_API_KEY set initially,
# so we handle validation carefully or allow lazy instantiation if needed.
settings = Settings()
