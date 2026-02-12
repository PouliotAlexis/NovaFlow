"""
NovaFlow - Service AI

Gère la communication avec le modèle AI (Local via Ollama ou Cloud via OpenAI).
Le choix est configurable dans les settings.
"""

import httpx
from core.config import settings


def _build_system_prompt(system_prompt: str, context: str = "") -> str:
    """Construit le system prompt avec injection de contexte RAG si disponible."""
    base = system_prompt or "Tu es NovaFlow, un assistant personnel intelligent. Réponds en français."
    
    if context:
        return (
            f"{base}\n\n"
            "## Contexte documentaire\n"
            "Voici des extraits pertinents des documents de l'utilisateur. "
            "Utilise ces informations pour répondre de manière précise et contextualisée. "
            "Cite les sources quand c'est pertinent.\n\n"
            f"{context}"
        )
    return base


async def chat_local(prompt: str, system_prompt: str = "", context: str = "") -> str:
    """
    Envoie une requête au modèle Ollama local.
    
    Args:
        prompt: Le message utilisateur.
        system_prompt: Instructions système optionnelles.
        context: Contexte RAG extrait des documents.
    
    Returns:
        La réponse du modèle.
    """
    full_system = _build_system_prompt(system_prompt, context)
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": prompt},
    ]

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_HOST}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


async def chat_cloud(prompt: str, system_prompt: str = "", context: str = "") -> str:
    """
    Envoie une requête au modèle Cloud (OpenAI).
    IMPORTANT: Le prompt doit être sanitizé AVANT d'appeler cette fonction.
    
    Args:
        prompt: Le message utilisateur (déjà sanitizé).
        system_prompt: Instructions système optionnelles.
        context: Contexte RAG extrait des documents.
    
    Returns:
        La réponse du modèle (contenant des tokens à desanitizer).
    """
    full_system = _build_system_prompt(system_prompt, context)
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": prompt},
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENAI_MODEL,
                "messages": messages,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def chat(
    prompt: str,
    system_prompt: str = "",
    mode: str | None = None,
    context: str = "",
) -> str:
    """
    Point d'entrée principal pour communiquer avec l'IA.
    
    Sélectionne automatiquement le mode (local/cloud) selon la config,
    ou utilise le mode spécifié en paramètre.
    
    Args:
        prompt: Le message utilisateur.
        system_prompt: Instructions système optionnelles.
        mode: Force le mode ("local" ou "cloud"). Si None, utilise la config.
        context: Contexte RAG extrait des documents.
    
    Returns:
        La réponse du modèle AI.
    """
    active_mode = mode or settings.AI_MODE

    if active_mode == "local":
        return await chat_local(prompt, system_prompt, context)
    elif active_mode == "cloud":
        return await chat_cloud(prompt, system_prompt, context)
    else:
        raise ValueError(f"Mode AI inconnu: {active_mode}")
