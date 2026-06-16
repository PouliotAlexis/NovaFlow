"""
NovaFlow - Service AI

Gère la communication avec le modèle AI :
  - Local via Ollama
  - Cloud via OpenAI
  - Cloud via Groq (API compatible OpenAI, gratuit)

Le choix est configurable dans les settings (AI_MODE).
"""

import json
import httpx
from typing import AsyncGenerator
from app.core.config import settings

def _build_system_prompt(system_prompt: str, context: str = "") -> str:
    """Construit le system prompt avec injection de contexte RAG si disponible."""
    base = system_prompt or "Tu es NovaFlow, un assistant personnel intelligent et élégant. Réponds TOUJOURS en utilisant un formatage Markdown riche et structuré (listes à puces, texte en gras, tableaux si pertinent). Utilise des emojis avec parcimonie pour agrémenter la réponse. Sépare tes paragraphes par des sauts de ligne clairs."
    
    if context:
        print(f"DEBUG AI: Context injected ({len(context)} chars).")
        res = (
            f"{base}\n\n"
            "## Outils Disponibles\n"
            "Tu peux effectuer des actions sur le système en utilisant des commandes spécifiques.\n"
            "- Pour ajouter une tâche à la liste : écris strictement `[TASK: Titre de la tâche]` sur une nouvelle ligne.\n"
            "  Exemple : 'Entendu, je le note.\n[TASK: Acheter du pain]'\n\n"
            "## Contexte documentaire\n"
            "Voici des extraits pertinents des documents de l'utilisateur. "
            f"IMPORTANT: Utilise UNIQUEMENT ces informations si elles permettent de répondre, sinon complète avec tes connaissances.\n"
            f"----------------\n{context}\n----------------\n\n"
        )
        return res
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


# =============================================================================
# Fonctions utilitaires pour les APIs compatibles OpenAI (OpenAI, Groq, etc.)
# =============================================================================

def _get_api_config(mode: str) -> tuple[str, str, str]:
    """Retourne (base_url, api_key, model) selon le mode AI."""
    if mode == "groq":
        return (
            "https://api.groq.com/openai/v1/chat/completions",
            settings.GROQ_API_KEY,
            settings.GROQ_MODEL,
        )
    else:  # "cloud" ou "openai"
        return (
            "https://api.openai.com/v1/chat/completions",
            settings.OPENAI_API_KEY,
            settings.OPENAI_MODEL,
        )


async def _chat_openai_compatible(
    prompt: str, system_prompt: str = "", context: str = "", mode: str = "cloud"
) -> str:
    """Requête non-streaming vers une API compatible OpenAI (OpenAI, Groq, etc.)."""
    full_system = _build_system_prompt(system_prompt, context)
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": prompt},
    ]
    
    url, api_key, model = _get_api_config(mode)
    print(f"[AI] Calling {mode} model: {model}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def _chat_openai_compatible_stream(
    prompt: str, system_prompt: str = "", context: str = "", mode: str = "cloud"
) -> AsyncGenerator[str, None]:
    """Streaming vers une API compatible OpenAI (OpenAI, Groq, etc.)."""
    full_system = _build_system_prompt(system_prompt, context)
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": prompt},
    ]
    
    url, api_key, model = _get_api_config(mode)
    print(f"[AI] Starting {mode} stream with model: {model}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": messages, "stream": True},
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


# =============================================================================
# Fonctions Ollama (Local)
# =============================================================================

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


async def chat_local_stream(
    prompt: str, system_prompt: str = "", context: str = ""
) -> AsyncGenerator[str, None]:
    """Ollama streaming — yields tokens one by one."""
    full_system = _build_system_prompt(system_prompt, context)
    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": prompt},
    ]
    payload = {"model": settings.OLLAMA_MODEL, "messages": messages, "stream": True}
    print(f"[AI] Calling local model: {settings.OLLAMA_MODEL} at {settings.OLLAMA_HOST} (Timeout: 300s)")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            f"{settings.OLLAMA_HOST}/api/chat",
            json=payload,
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
                        print(f"\n[AI] Local stream finished. (Total response length: {data.get('total_duration', 0)}ns)")
                        break
                except json.JSONDecodeError:
                    continue


# =============================================================================
# Points d'entrée principaux
# =============================================================================

async def chat_stream(
    prompt: str,
    system_prompt: str = "",
    mode: str | None = None,
    context: str = "",
) -> AsyncGenerator[str, None]:
    """Point d'entrée streaming — sélectionne local, openai, groq ou cloud."""
    active_mode = mode or settings.AI_MODE
    print(f"[AI] Starting stream in mode: {active_mode}")
    
    if active_mode == "local":
        async for token in chat_local_stream(prompt, system_prompt, context):
            yield token
    elif active_mode in ("cloud", "openai", "groq"):
        async for token in _chat_openai_compatible_stream(prompt, system_prompt, context, mode=active_mode):
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
    
    Sélectionne automatiquement le mode selon la config :
      - "local"  → Ollama (privé, sur la machine)
      - "cloud"  → OpenAI API
      - "openai" → OpenAI API (alias de cloud)
      - "groq"   → Groq API (Llama 3.3, gratuit)
    
    Args:
        prompt: Le message utilisateur.
        system_prompt: Instructions système optionnelles.
        mode: Force le mode. Si None, utilise la config.
        context: Contexte RAG extrait des documents.
    
    Returns:
        La réponse du modèle AI.
    """
    active_mode = mode or settings.AI_MODE

    if active_mode == "local":
        return await chat_local(prompt, system_prompt, context)
    elif active_mode in ("cloud", "openai", "groq"):
        return await _chat_openai_compatible(prompt, system_prompt, context, mode=active_mode)
    else:
        raise ValueError(f"Mode AI inconnu: {active_mode}")
