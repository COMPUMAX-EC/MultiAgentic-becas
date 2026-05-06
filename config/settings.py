"""
MultiAgentic-Becas — Configuración centralizada
Lee variables desde .env y expone un objeto `settings` global.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ---- App ----
    app_name: str = Field(default="MultiAgentic-Becas")
    log_level: str = Field(default="INFO")

    # ---- LLM Backend ----
    llm_backend: str = Field(default="ollama")  # "amd_cloud" | "ollama"

    # ---- AMD Developer Cloud / vLLM ----
    vllm_base_url: str = Field(default="http://localhost:8000/v1")
    vllm_api_key: str = Field(default="not-required")
    vllm_model: str = Field(default="meta-llama/Llama-3.1-70B-Instruct")

    # ---- Ollama (desarrollo local) ----
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1")

    # ---- Embeddings ----
    embedding_model: str = Field(default="all-MiniLM-L6-v2")

    # ---- ChromaDB ----
    chroma_persist_dir: str = Field(default="./data/chroma")

    # ---- Búsqueda ----
    max_scholarships_per_search: int = Field(default=10)
    max_search_results: int = Field(default=5)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
