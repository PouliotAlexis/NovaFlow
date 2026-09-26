"""
NovaFlow - Discord Bot Client

Configuration du client Discord (intents, préfixe) et gestion
de la connexion / déconnexion du bot.
"""

import discord
from discord.ext import commands
from app.core.config import settings


def create_bot() -> commands.Bot:
    """
    Crée et retourne une instance du bot Discord NovaFlow.

    Le bot utilise les intents suivants :
    - default() : permet les événements de base (guilds, messages, etc.)
    - message_content : permet de lire le contenu des messages (nécessaire pour les commandes texte)
    """
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix="!",
        intents=intents,
        description="NovaFlow — Ton assistant d'étude intelligent 🎓",
    )

    @bot.event
    async def on_ready():
        """Événement déclenché quand le bot est connecté et prêt."""
        # Synchroniser les commandes slash avec Discord
        await bot.tree.sync()
        print(f"{'='*50}")
        print(f"🚀 NovaFlow Bot connecté : {bot.user} (ID: {bot.user.id})")
        print(f"📡 Commandes slash synchronisées")
        print(f"🏠 Serveurs : {len(bot.guilds)}")
        print(f"{'='*50}")

        # Définir le statut du bot
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="tes devoirs 📚"
        )
        await bot.change_presence(activity=activity)

    @bot.event
    async def on_command_error(ctx, error):
        """Gestion globale des erreurs de commandes textuelles."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignorer les commandes inconnues
        print(f"[BOT ERROR] {type(error).__name__}: {error}")

    return bot
