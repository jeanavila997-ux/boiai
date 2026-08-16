"""Configuração central do backend BoiAI (lê de variáveis de ambiente)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://boiai:boiai_secret@localhost:3306/boiai"
    qdrant_url: str = "http://localhost:6333"

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embed_model: str = "bge-m3"
    ollama_think: str = "medium"  # false|true|low|medium|high

    api_jwt_secret: str = "troque-esta-chave-em-producao"
    api_jwt_expires_min: int = 43200

    # Coleções Qdrant
    qdrant_col_knowledge: str = "knowledge"
    qdrant_col_memory: str = "agent_memory"
    embed_dim: int = 1024  # bge-m3


settings = Settings()
