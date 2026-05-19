from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    defectdojo_base_url: str = os.getenv("DEFECTDOJO_BASE_URL", "http://localhost:8080")
    defectdojo_api_token: str = os.getenv("DEFECTDOJO_API_TOKEN", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    llm_enabled: bool = os.getenv("LLM_ENABLED", "false").lower() == "true"
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    llm_model: str = os.getenv("LLM_MODEL", "llama3-70b-8192")


settings = Settings()
