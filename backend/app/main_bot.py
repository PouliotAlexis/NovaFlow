"""
NovaFlow — Point d'entrée pour l'exécution du Bot Discord

Lance le bot Discord NovaFlow avec tous les cogs (modules de commandes).

Usage:
    cd backend
    python -m app.main_bot
"""

import sys
import asyncio

# Fix Windows pour les sous-processus async (Playwright etc.)
if sys.platform == "win32":
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("[WINDOWS FIX] ProactorEventLoopPolicy appliqué.")
    except Exception as e:
        print(f"[WINDOWS FIX] Erreur: {e}")

import os

# S'assurer que le répertoire backend est dans le PYTHONPATH
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.bot.client import create_bot


async def main():
    """Point d'entrée principal du bot Discord."""
    bot = create_bot()

    # Vérifier que le token est configuré
    if not settings.DISCORD_BOT_TOKEN:
        print("=" * 60)
        print("❌ ERREUR : DISCORD_BOT_TOKEN non configuré !")
        print()
        print("Pour configurer le bot Discord :")
        print("1. Va sur https://discord.com/developers/applications")
        print("2. Crée une application et un bot")
        print("3. Copie le token du bot")
        print("4. Ajoute dans backend/.env :")
        print('   DISCORD_BOT_TOKEN="ton_token_ici"')
        print('   DISCORD_USER_ID=ton_id_discord_numerique')
        print("=" * 60)
        return

    if not settings.DISCORD_USER_ID:
        print("⚠️  ATTENTION : DISCORD_USER_ID non configuré.")
        print("   Les notifications proactives (briefings, sync Moodle) ne fonctionneront pas.")
        print("   Ajoute dans backend/.env : DISCORD_USER_ID=ton_id_discord_numerique")
        print()

    # Charger les extensions (cogs)
    cogs = [
        "app.bot.cogs.rag_cog",       # /ask, /search
        "app.bot.cogs.schedule_cog",   # /devoirs, /taches, /planifier, /cours
        "app.bot.cogs.tasks_cog",      # Tâches périodiques (sync Moodle, briefings)
    ]

    async with bot:
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f"  ✅ Cog chargé : {cog}")
            except Exception as e:
                print(f"  ❌ Erreur chargement {cog}: {e}")

        print()
        print("🚀 Démarrage du bot Discord NovaFlow...")
        print(f"   Mode IA : {settings.AI_MODE}")
        print(f"   Moodle  : {settings.MOODLE_URL}")
        print()

        await bot.start(settings.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
