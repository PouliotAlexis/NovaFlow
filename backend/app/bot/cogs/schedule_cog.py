"""
NovaFlow - Schedule Cog (Commandes slash pour le planning et les devoirs)

Expose les commandes /devoirs, /taches et /planifier
qui interagissent avec les services de gestion de tâches et d'événements.
"""

import datetime
import os
import json
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from app.core.config import settings
from app.services.task_manager import TaskManager
from app.services.event_manager import EventManager
from app.services.ai_engine import chat


def _priority_emoji(priority: str) -> str:
    """Retourne un emoji selon la priorité."""
    return {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢",
    }.get(priority, "⚪")


def _days_until(due_date_str: str) -> Optional[int]:
    """Calcule le nombre de jours restants avant une échéance."""
    if not due_date_str or due_date_str == "N/A":
        return None
    try:
        due = datetime.datetime.fromisoformat(due_date_str.replace("Z", "+00:00").split(".")[0])
        now = datetime.datetime.now()
        return (due - now).days
    except Exception:
        return None


def _urgency_bar(days_left: Optional[int]) -> str:
    """Retourne une barre visuelle d'urgence."""
    if days_left is None:
        return "⬜⬜⬜⬜⬜"
    if days_left <= 1:
        return "🟥🟥🟥🟥🟥"
    elif days_left <= 3:
        return "🟧🟧🟧🟧⬜"
    elif days_left <= 7:
        return "🟨🟨🟨⬜⬜"
    elif days_left <= 14:
        return "🟩🟩⬜⬜⬜"
    else:
        return "🟦⬜⬜⬜⬜"


def _get_courses_list() -> list[dict]:
    """Charge la liste des cours synchronisés depuis le disque."""
    dest_dir = settings.MOODLE_DOWNLOADS_DESTINATION
    if not os.path.exists(dest_dir):
        return []

    courses = []
    for cid in os.listdir(dest_dir):
        course_path = os.path.join(dest_dir, cid)
        if os.path.isdir(course_path):
            name = f"Cours {cid}"
            info_path = os.path.join(course_path, "course_info.json")
            if os.path.exists(info_path):
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        raw_name = info.get("name", name)
                        # Nettoyer le nom (enlever le code session)
                        if " - " in raw_name:
                            parts = raw_name.split(" - ", 1)
                            if any(c.isdigit() for c in parts[0]):
                                raw_name = parts[1].strip()
                        name = raw_name
                except Exception:
                    pass
            courses.append({"id": cid, "name": name})
    return courses


class ScheduleCog(commands.Cog):
    """Commandes slash pour la gestion du planning et des devoirs."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /devoirs ─────────────────────────────────────────────────
    @app_commands.command(
        name="devoirs",
        description="Affiche tes devoirs et échéances en cours, classés par urgence"
    )
    @app_commands.describe(
        cours="Filtrer par ID de cours (optionnel)"
    )
    async def devoirs_command(
        self,
        interaction: discord.Interaction,
        cours: Optional[str] = None,
    ):
        await interaction.response.defer(thinking=True)

        tasks = TaskManager.instance().get_all_tasks()

        # Filtrer les tâches non terminées
        pending = [t for t in tasks if not t.get("done", False)]

        # Filtrer par cours si spécifié
        if cours:
            pending = [t for t in pending if str(t.get("course_id", "")) == str(cours)]

        if not pending:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="✅ Aucun devoir en attente",
                    description="Tu es à jour ! 🎉" if not cours else f"Aucun devoir pour le cours `{cours}`.",
                    color=discord.Color.green(),
                )
            )
            return

        # Trier par urgence (jours restants croissant, None à la fin)
        def sort_key(t):
            days = _days_until(t.get("due_date"))
            return days if days is not None else 9999

        pending.sort(key=sort_key)

        # Construire l'embed
        embed = discord.Embed(
            title="📋 Devoirs & Échéances",
            description=f"**{len(pending)}** tâche(s) en attente",
            color=discord.Color.from_rgb(245, 158, 11),  # Amber
            timestamp=datetime.datetime.now(),
        )

        for i, task in enumerate(pending[:15]):  # Limiter à 15 pour ne pas dépasser
            days = _days_until(task.get("due_date"))
            due_str = task.get("due_date", "Pas de date")
            if days is not None:
                if days < 0:
                    due_str = f"⚠️ **EN RETARD** ({abs(days)}j)"
                elif days == 0:
                    due_str = "🔥 **AUJOURD'HUI**"
                elif days == 1:
                    due_str = "⏰ **DEMAIN**"
                else:
                    due_str = f"📅 {days}j restants"

            priority = task.get("priority", "medium")
            course = task.get("course_id", "—")

            embed.add_field(
                name=f"{_priority_emoji(priority)} {task['title'][:50]}",
                value=f"{_urgency_bar(days)} {due_str}\n`Cours: {course}`",
                inline=False,
            )

        if len(pending) > 15:
            embed.set_footer(text=f"... et {len(pending) - 15} autres tâches")

        await interaction.followup.send(embed=embed)

    # ── /taches ──────────────────────────────────────────────────
    @app_commands.command(
        name="taches",
        description="Gère tes tâches : ajouter, cocher ou supprimer"
    )
    @app_commands.describe(
        action="Action à effectuer",
        titre="Titre de la nouvelle tâche (pour 'ajouter')",
        id="ID de la tâche (pour 'cocher' ou 'supprimer')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="📝 Ajouter une tâche", value="ajouter"),
        app_commands.Choice(name="✅ Cocher (terminée)", value="cocher"),
        app_commands.Choice(name="🗑️ Supprimer", value="supprimer"),
    ])
    async def taches_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        titre: Optional[str] = None,
        id: Optional[str] = None,
    ):
        tm = TaskManager.instance()

        if action.value == "ajouter":
            if not titre:
                await interaction.response.send_message(
                    "❌ Tu dois fournir un `titre` pour ajouter une tâche.",
                    ephemeral=True,
                )
                return

            result = tm.add_task(title=titre, priority="medium")
            embed = discord.Embed(
                title="✅ Tâche ajoutée",
                description=f"**{titre}**",
                color=discord.Color.green(),
            )
            embed.add_field(name="ID", value=f"`{result['id'][:8]}...`")
            await interaction.response.send_message(embed=embed)

        elif action.value == "cocher":
            if not id:
                await interaction.response.send_message(
                    "❌ Tu dois fournir l'`id` de la tâche à cocher.",
                    ephemeral=True,
                )
                return

            result = tm.toggle_task(id)
            if result:
                status = "✅ Terminée" if result["done"] else "🔄 Rouverte"
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title=f"{status}",
                        description=f"**{result['title']}**",
                        color=discord.Color.green() if result["done"] else discord.Color.orange(),
                    )
                )
            else:
                await interaction.response.send_message("❌ Tâche introuvable.", ephemeral=True)

        elif action.value == "supprimer":
            if not id:
                await interaction.response.send_message(
                    "❌ Tu dois fournir l'`id` de la tâche à supprimer.",
                    ephemeral=True,
                )
                return

            success = tm.delete_task(id)
            if success:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="🗑️ Tâche supprimée",
                        color=discord.Color.greyple(),
                    )
                )
            else:
                await interaction.response.send_message("❌ Tâche introuvable.", ephemeral=True)

    # ── /planifier ───────────────────────────────────────────────
    @app_commands.command(
        name="planifier",
        description="Génère un plan d'étude optimisé pour les prochaines 48h"
    )
    async def planifier_command(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        try:
            # Récupérer les tâches en cours
            tasks = TaskManager.instance().get_all_tasks()
            pending = [t for t in tasks if not t.get("done", False)]

            if not pending:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="✅ Rien à planifier",
                        description="Tu n'as aucune tâche en attente !",
                        color=discord.Color.green(),
                    )
                )
                return

            # Préparer le résumé des tâches pour l'IA
            tasks_summary = ""
            for t in pending[:20]:
                days = _days_until(t.get("due_date"))
                days_str = f"{days}j restants" if days is not None else "pas de date"
                tasks_summary += f"- {t['title']} (Priorité: {t.get('priority', 'medium')}, {days_str}, Cours: {t.get('course_id', 'N/A')})\n"

            # Récupérer les cours connus
            courses = _get_courses_list()
            courses_ctx = "\n".join([f"- {c['name']} (ID: {c['id']})" for c in courses]) or "Aucun cours synchronisé."

            now = datetime.datetime.now()
            prompt = f"""Aujourd'hui nous sommes le {now.strftime('%A %d %B %Y à %H:%M')}.

Voici mes tâches en cours :
{tasks_summary}

Mes cours :
{courses_ctx}

Génère un plan d'étude optimisé pour les prochaines 48 heures.
- Priorise les tâches par urgence (échéance la plus proche) et difficulté.
- Propose des blocs de 45-90 minutes avec des pauses.
- Utilise des emojis et un format visuel clair.
- Sois concis et actionnable."""

            plan_text = await chat(
                prompt=prompt,
                system_prompt="Tu es NovaFlow, un planificateur d'études expert. Génère des plans d'étude optimisés et motivants. Réponds en français avec du formatage Markdown.",
            )

            embed = discord.Embed(
                title="📅 Plan d'étude — Prochaines 48h",
                description=plan_text[:4000],
                color=discord.Color.from_rgb(139, 92, 246),  # Violet
                timestamp=now,
            )
            embed.set_footer(text="🤖 Généré par NovaFlow AI")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Erreur",
                    description=f"Impossible de générer le plan : ```{str(e)[:500]}```",
                    color=discord.Color.red(),
                )
            )

    # ── /cours ───────────────────────────────────────────────────
    @app_commands.command(
        name="cours",
        description="Affiche la liste de tes cours synchronisés depuis Moodle"
    )
    async def cours_command(self, interaction: discord.Interaction):
        courses = _get_courses_list()

        if not courses:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="📚 Aucun cours",
                    description="Aucun cours synchronisé. Lance une synchronisation Moodle d'abord !",
                    color=discord.Color.orange(),
                )
            )
            return

        embed = discord.Embed(
            title="📚 Mes cours Moodle",
            description=f"**{len(courses)}** cours synchronisés",
            color=discord.Color.from_rgb(59, 130, 246),  # Blue
        )

        for c in courses[:25]:  # Limite Discord : 25 fields max
            embed.add_field(
                name=f"📖 {c['name'][:50]}",
                value=f"ID: `{c['id']}`",
                inline=True,
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Point d'entrée pour charger le cog."""
    await bot.add_cog(ScheduleCog(bot))
