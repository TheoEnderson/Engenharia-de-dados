"""Criação tardia do cliente MongoDB.

Importar este módulo nunca abre uma conexão. A dependência pymongo também só é
carregada quando uma operação remota foi explicitamente autorizada.
"""

from __future__ import annotations

from typing import Any

from config import get_settings


def create_mongo_client() -> tuple[Any, Any]:
    """Cria cliente e database configurados e confirma a conectividade."""
    settings = get_settings(require_mongodb=True)
    try:
        from pymongo import MongoClient
    except ImportError as exc:  # pragma: no cover - depende do ambiente remoto
        raise RuntimeError(
            "A dependência pymongo não está instalada. Instale requirements.txt."
        ) from exc

    client = MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    try:
        client.admin.command("ping")
    except Exception:
        client.close()
        raise
    return client, client[settings.mongodb_database]
