"""Environment-backed configuration for Dante."""
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    ollama_host: str = "http://localhost:11434"
    model: str = "llama3.2"
    db_path: Path = Path("data/dante.sqlite3")
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    seed: int | None = None
    system_prompt: str = (
        "You are Dante, an experimental local agent. Be honest about uncertainty "
        "and propose only bounded, relevant next steps."
    )

    @field_validator("ollama_host")
    @classmethod
    def host_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("OLLAMA_HOST cannot be empty")
        return value.rstrip("/")

    @field_validator("model")
    @classmethod
    def model_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DANTE_MODEL cannot be empty")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    raw_seed = os.getenv("DANTE_SEED")
    return Settings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        model=os.getenv("DANTE_MODEL", "llama3.2"),
        db_path=Path(os.getenv("DANTE_DB_PATH", "data/dante.sqlite3")),
        temperature=float(os.getenv("DANTE_TEMPERATURE", "0.8")),
        seed=int(raw_seed) if raw_seed not in (None, "") else None,
        system_prompt=os.getenv(
            "DANTE_SYSTEM_PROMPT",
            "You are Dante, an experimental local agent. Be honest about uncertainty "
            "and propose only bounded, relevant next steps.",
        ),
    )
