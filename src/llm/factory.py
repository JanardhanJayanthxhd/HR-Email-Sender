from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from src.config import Settings


def build_ollama_llm(settings: Settings) -> BaseChatModel:
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        num_ctx=settings.ollama_num_ctx,
    )


def build_google_llm(settings: Settings) -> BaseChatModel:
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY required when LLM_PROVIDER=google")
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise RuntimeError("Install the 'google' extra to use Google Gemini") from exc
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=settings.llm_temperature,
    )


_PROVIDERS: dict[str, Callable[[Settings], BaseChatModel]] = {
    "ollama": build_ollama_llm,
    "google": build_google_llm,
}


def get_llm(settings: Settings) -> BaseChatModel:
    """Create the configured LangChain chat model."""
    provider = settings.llm_provider.lower()
    try:
        builder = _PROVIDERS[provider]
    except KeyError as exc:
        raise ValueError(f"Unknown provider: {provider}") from exc
    return builder(settings)
