from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # These will automatically look for these names in your .env file
    SUPABASE_DATABASE: str
    GEMINI_API_KEY: str # Google Gemini API key

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings():
    return Settings()
