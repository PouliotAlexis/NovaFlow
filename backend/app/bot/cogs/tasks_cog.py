"""
NovaFlow - Tasks Cog (Tâches périodiques proactives)

Tâches d'arrière-plan qui tournent automatiquement :
- Synchronisation Moodle toutes les 3 heures
- Briefing du matin (07:30)
- Check-in du soir (21:30)
"""

import datetime
import os
import json
from typing import Optional

import discord
from discord.ext import tasks, commands

from app.core.config import settings
from app.services.task_manager import TaskManager
from app.services.ai_engine import chat
from app.bot.ui.views import DailyCheckinView


def _days_until(due_date_str: str) -> Optional[int]:
    """Calcule le nombre de jours restants."""
    if not due_date_str or due_date_str == "N/A":
        return None
    try:
        due = datetime.datetime.fromisoformat(due_date_str.replace("Z", "+00:00").split(".")[0])
        return (due - datetime.datetime.now()).days
    except Exception:
        return None


class TasksCog(commands.Cog):
    """Tâches périodiques : synchronisation Moodle et notifications automatiques."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Démarrer les boucles de tâches
        self.moodle_sync.start()
        self.scheduled_briefings.start()
        print("[TASKS COG] ✅ Tâches périodiques démarrées (sync Moodle + briefings)")

    def cog_unload(self):
        """Appelé quand le cog est déchargé — annule les tâches."""
        self.moodle_sync.cancel()
        self.scheduled_briefings.cancel()

    async def _get_user(self) -> Optional[discord.User]:
        """Récupère l'utilisateur Discord configuré."""
        user_id = settings.DISCORD_USER_ID
        if not user_id:
            return None
        try:
            return await self.bot.fetch_user(user_id)
        except Exception as e:
            print(f"[TASKS COG] ⚠️ Impossible de récupérer l'utilisateur {user_id}: {e}")
            return None

    # ── Synchronisation Moodle ───────────────────────────────────
    @tasks.loop(hours=3)
    async def moodle_sync(self):
        """Vérifie les mises à jour Moodle toutes les 3 heures."""
        print(f"[MOODLE SYNC TASK] 🔄 Vérification automatique des mises à jour...")

        try:
            # Charger le token Moodle stocké
            token_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data", "moodle_token.json"
            )

            if not os.path.exists(token_file):
                print("[MOODLE SYNC TASK] ⚠️ Aucun token Moodle stocké. Skip.")
                return

            with open(token_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)
                token = token_data.get("token")

            if not token:
                print("[MOODLE SYNC TASK] ⚠️ Token vide. Skip.")
                return

            # Importer et exécuter la synchronisation
            from app.services.moodle_sync_service import sync_moodle_courses

            moodle_url = settings.MOODLE_URL or "https://moodle.usherbrooke.ca"
            results = await sync_moodle_courses(
                username=None,
                password=None,
                url=moodle_url,
                token=token,
            )

            # Notifier l'utilisateur s'il y a de nouveaux éléments
            new_items = [r for r in (results or []) if r.get("status") == "synced"]
            if new_items:
                user = await self._get_user()
                if user:
                    embed = discord.Embed(
                        title="📚 Mise à jour Moodle",
                        description=f"**{len(new_items)}** nouveau(x) fichier(s) synchronisé(s) :",
                        color=discord.Color.from_rgb(16, 185, 129),
                        timestamp=datetime.datetime.now(),
                    )
                    for item in new_items[:10]:
                        embed.add_field(
                            name=f"📄 {item.get('file', '?')[:50]}",
                            value=f"Cours : {item.get('course', '?')[:30]}",
                            inline=True,
                        )
                    if len(new_items) > 10:
                        embed.set_footer(text=f"... et {len(new_items) - 10} autres")

                    await user.send(embed=embed)
            else:
                print("[MOODLE SYNC TASK] ✅ Aucune mise à jour détectée.")

        except Exception as e:
            print(f"[MOODLE SYNC TASK] ❌ Erreur: {e}")

    @moodle_sync.before_loop
    async def before_moodle_sync(self):
        """Attendre que le bot soit prêt avant de démarrer la boucle."""
        await self.bot.wait_until_ready()

    # ── Briefings automatiques ───────────────────────────────────
    @tasks.loop(minutes=1)
    async def scheduled_briefings(self):
        """Vérifie toutes les minutes s'il faut envoyer un briefing."""
        current_time = datetime.datetime.now().strftime("%H:%M")

        # ── Briefing du matin (07:30) ────────────────────────────
        if current_time == "07:30":
            user = await self._get_user()
            if not user:
                return

            try:
                embed = await self._build_morning_briefing()
                await user.send(embed=embed)
                print("[BRIEFING] ☀️ Briefing du matin envoyé !")
            except Exception as e:
                print(f"[BRIEFING] ❌ Erreur briefing matin: {e}")

        # ── Check-in du soir (21:30) ─────────────────────────────
        elif current_time == "21:30":
            user = await self._get_user()
            if not user:
                return

            try:
                embed = discord.Embed(
                    title="🌙 Bilan du soir",
                    description="As-tu pu avancer sur tes objectifs d'aujourd'hui ?",
                    color=discord.Color.from_rgb(139, 92, 246),  # Violet
                    timestamp=datetime.datetime.now(),
                )

                # Montrer les tâches dues aujourd'hui
                tasks = TaskManager.instance().get_all_tasks()
                today_tasks = []
                for t in tasks:
                    days = _days_until(t.get("due_date"))
                    if days is not None and days <= 1 and not t.get("done"):
                        today_tasks.append(t)

                if today_tasks:
                    tasks_text = "\n".join([f"- {'✅' if t.get('done') else '⬜'} {t['title']}" for t in today_tasks[:8]])
                    embed.add_field(name="📋 Tâches d'aujourd'hui", value=tasks_text, inline=False)

                view = DailyCheckinView()
                await user.send(embed=embed, view=view)
                print("[BRIEFING] 🌙 Check-in du soir envoyé !")

            except Exception as e:
                print(f"[BRIEFING] ❌ Erreur check-in soir: {e}")

    @scheduled_briefings.before_loop
    async def before_scheduled_briefings(self):
        """Attendre que le bot soit prêt."""
        await self.bot.wait_until_ready()

    async def _build_morning_briefing(self) -> discord.Embed:
        """Construit l'embed du briefing du matin."""
        now = datetime.datetime.now()
        tasks = TaskManager.instance().get_all_tasks()

        # Tâches urgentes (dues aujourd'hui ou en retard)
        urgent = []
        upcoming = []
        for t in tasks:
            if t.get("done"):
                continue
            days = _days_until(t.get("due_date"))
            if days is not None:
                if days <= 0:
                    urgent.append(t)
                elif days <= 3:
                    upcoming.append(t)

        embed = discord.Embed(
            title=f"☀️ Bonjour ! — {now.strftime('%A %d %B')}",
            color=discord.Color.from_rgb(251, 191, 36),  # Amber
            timestamp=now,
        )

        # Résumé
        total_pending = len([t for t in tasks if not t.get("done")])
        embed.description = f"Tu as **{total_pending}** tâche(s) en attente."

        # Tâches urgentes
        if urgent:
            urgent_text = "\n".join([f"🔴 {t['title'][:50]}" for t in urgent[:5]])
            embed.add_field(name="🚨 Urgent (aujourd'hui / en retard)", value=urgent_text, inline=False)

        # Tâches à venir (3 jours)
        if upcoming:
            upcoming_text = "\n".join([
                f"🟡 {t['title'][:50]} ({_days_until(t.get('due_date'))}j)"
                for t in upcoming[:5]
            ])
            embed.add_field(name="📅 Prochaines échéances (3 jours)", value=upcoming_text, inline=False)

        if not urgent and not upcoming:
            embed.add_field(name="🎉 Tout est calme", value="Pas d'échéance urgente. Profites-en pour avancer !", inline=False)

        embed.set_footer(text="🤖 NovaFlow — Briefing quotidien")
        return embed


async def setup(bot: commands.Bot):
    """Point d'entrée pour charger le cog."""
    await bot.add_cog(TasksCog(bot))
