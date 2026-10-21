"""Run Dante as an interactive terminal conversation."""
from dante.agent import DanteAgent
from dante.config import get_settings
from dante.llm import LLMError


def main() -> None:
    settings = get_settings()
    agent = DanteAgent(settings)
    print(f"Dante local prototype (model: {settings.model})")
    print("Type /exit to quit. This prototype does not execute external actions.")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDante stopped.")
            break
        if text.lower() in {"/exit", "/quit"}:
            print("Dante stopped.")
            break
        if not text:
            continue
        try:
            print(f"\nDante: {agent.respond(text)}")
        except LLMError as exc:
            print(f"\n[Ollama error] {exc}")
        except Exception as exc:
            print(f"\n[Unexpected error] {exc}")


if __name__ == "__main__":
    main()
