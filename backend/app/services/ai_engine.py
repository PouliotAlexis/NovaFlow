"""
NovaFlow - Service AI

Gère la communication avec le modèle AI (Local via Ollama ou Cloud via OpenAI).
Le choix est configurable dans les settings.
"""

import json
import httpx
from typing import AsyncGenerator
from app.core.config import settings


def _build_system_prompt(system_prompt: str, context: str = "") -> str:
    """Construit le system prompt avec injection de contexte RAG si disponible."""
    base = system_prompt or "Tu es NovaFlow, un assistant personnel intelligent et élégant. Réponds TOUJOURS en utilisant un formatage Markdown riche et structuré (listes à puces, texte en gras, tableaux si pertinent). Utilise des emojis avec parcimonie pour agrémenter la réponse. Sépare tes paragraphes par des sauts de ligne clairs."
    
    if context:
        return (
            f"{base}\n\n"
            "## Outils Disponibles\n"
            "Tu peux effectuer des actions sur le système en utilisant des commandes spécifiques.\n"
            "- Pour ajouter une tâche à la liste : écris strictement `[TASK: Titre de la tâche]` sur une nouvelle ligne.\n"
            "  Exemple : 'Entendu, je le note.\n[TASK: Acheter du pain]'\n\n"
            "## Contexte documentaire\n"
            "Voici des extraits pertinents des documents de l'utilisateur. "
            "Utilise ces informations pour répondre de manière précise et contextualisée. "
            "Cite les sources quand c'est pertinent.\n\n"
            f"{context}"
        )
    else:
        # Même sans contexte RAG, on veut que l'IA sache utiliser les outils
        return (
            f"{base}\n\n"
            "## Outils Disponibles\n"
            "Tu peux effectuer des actions sur le système en utilisant des commandes spécifiques.\n"
            "- Pour ajouter une tâche à la liste : écris strictement `[TASK: Titre de la tâche]` sur une nouvelle ligne.\n"
            "  Exemple : 'Entendu, je le note.\n[TASK: Acheter du pain]'\n"
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

    async with httpx.AsyncClient(timeout=600.0) as client:
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


async def chat_local_stream(
    prompt: str, system_prompt: str = "", context: str = ""
) -> AsyncGenerator[str, None]:
    """Ollama streaming — yields tokens one by one."""
    full_system = _build_system_prompt(system_prompt, context)
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": prompt},
    ]
    async with httpx.AsyncClient(timeout=600.0) as client:
        async with client.stream(
            "POST",
            f"{settings.OLLAMA_HOST}/api/chat",
            json={"model": settings.OLLAMA_MODEL, "messages": messages, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue


async def chat_cloud_stream(
    prompt: str, system_prompt: str = "", context: str = ""
) -> AsyncGenerator[str, None]:
    """OpenAI streaming — yields tokens one by one."""
    full_system = _build_system_prompt(system_prompt, context)
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": prompt},
    ]
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": settings.OPENAI_MODEL, "messages": messages, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    token = data["choices"][0]["delta"].get("content", "")
                    if token:
                        yield token
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def chat_stream(
    prompt: str,
    system_prompt: str = "",
    mode: str | None = None,
    context: str = "",
) -> AsyncGenerator[str, None]:
    """Point d'entrée streaming — sélectionne local ou cloud."""
    active_mode = mode or settings.AI_MODE
    if active_mode == "local":
        async for token in chat_local_stream(prompt, system_prompt, context):
            yield token
    elif active_mode == "cloud":
        async for token in chat_cloud_stream(prompt, system_prompt, context):
            yield token
    else:
        raise ValueError(f"Mode AI inconnu: {active_mode}")


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
