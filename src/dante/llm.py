"""Small Ollama adapter; no external actions are executed here."""
from ollama import Client
from pydantic import BaseModel

from dante.config import Settings


class LLMError(RuntimeError):
    """Raised when the local model cannot produce a usable response."""


class OllamaLLM:
    def __init__(self, settings: Settings, client: Client | None = None) -> None:
        self.model = settings.model
        self.client = client or Client(host=settings.ollama_host)
        self.options: dict[str, int | float] = {
            "temperature": settings.temperature,
        }
        if settings.seed is not None:
            self.options["seed"] = settings.seed

    def chat(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self.client.chat(
                model=self.model, messages=messages, options=self.options
            )
            content = response.message.content
            if not content or not content.strip():
                raise LLMError("The local model returned an empty response.")
            return content.strip()
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(
                "Could not get a response from Ollama. Check that Ollama is running "
                "and that the configured model is installed."
            ) from exc

    def structured(self, messages: list[dict[str, str]], schema: type[BaseModel]) -> BaseModel:
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                format=schema.model_json_schema(),
                options=self.options,
            )
            content = response.message.content
            if not content:
                raise LLMError("The local model returned an empty structured response.")
            return schema.model_validate_json(content)
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError("The local model did not return valid structured output.") from exc
