"""
MultiAgentic-Becas — LLM Client Factory
Crea el cliente LLM según el backend configurado:
  - "amd_cloud": vLLM en AMD Instinct MI300X (OpenAI-compatible API)
  - "ollama": Ollama local para desarrollo sin GPU
"""
from langchain_openai import ChatOpenAI
from langchain_community.llms.ollama import Ollama
from langchain_core.language_models import BaseChatModel

from config.settings import settings
from loguru import logger


def get_llm(temperature: float = 0.1) -> BaseChatModel:
    """
    Retorna el cliente LLM configurado.

    Args:
        temperature: Creatividad del modelo (0.0 = determinista, 1.0 = creativo)

    Returns:
        Instancia de BaseChatModel lista para usar con LangChain/LangGraph
    """
    backend = settings.llm_backend.lower()

    if backend == "amd_cloud":
        logger.info(
            f"🔴 Usando AMD Developer Cloud vLLM: {settings.vllm_model} "
            f"en {settings.vllm_base_url}"
        )
        return ChatOpenAI(
            model=settings.vllm_model,
            base_url=settings.vllm_base_url,
            api_key=settings.vllm_api_key,
            temperature=temperature,
            max_tokens=4096,
        )

    elif backend == "ollama":
        logger.info(
            f"🟡 Usando Ollama local: {settings.ollama_model} "
            f"en {settings.ollama_base_url}"
        )
        # ChatOpenAI también funciona con Ollama vía endpoint OpenAI-compatible
        return ChatOpenAI(
            model=settings.ollama_model,
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
            temperature=temperature,
            max_tokens=4096,
        )

    else:
        raise ValueError(
            f"Backend LLM desconocido: '{backend}'. "
            "Usa 'amd_cloud' o 'ollama' en tu .env"
        )
